import json
import os
import time
from typing import List, Literal, Optional, Dict
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.core.tidal_auth import get_tidal_session, tidal_status, start_device_login, refresh_session_if_needed, logout_tidal_session
from backend.app.core.database import get_db
from backend.app.models.download import DownloadTask, DownloadStatus
from backend.app.tasks.tidal_tasks import tidal_download_track

router = APIRouter(prefix="/tidal", tags=["Tidal"])

class TidalItem(BaseModel):
    id: int
    title: str
    artist: Optional[str] = None
    album_name: Optional[str] = None
    image: Optional[str] = None

class SearchResponse(BaseModel):
    items: List[TidalItem]

class TidalDownloadBody(BaseModel):
    id: int = Field(..., description="ID de Tidal")
    type: Literal["track", "album"] = Field(..., description="Tipo de descarga")

class TidalEnqueueResponse(BaseModel):
    enqueued: int
    items: List[Dict[str, str]]

def _get_user_display_name(session) -> Optional[str]:
    try:
        u = getattr(session, "user", None)
    except Exception:
        u = None
    if not u:
        return None
    return getattr(u, "first_name", None) or getattr(u, "username", None) or getattr(u, "name", None)

def _get_country_code(session) -> str:
    return getattr(session, "country_code", None) or getattr(session, "countryCode", None) or "unknown"

def _search_with_tidalapi(session, query: str, models: Optional[List[object]] = None):
    if models:
        try:
            return session.search(query, models=models)
        except TypeError:
            pass
        except Exception:
            pass
    try:
        return session.search(query=query)
    except TypeError:
        return session.search(query)

def _extract_items(result, key: str):
    if isinstance(result, dict):
        return result.get(key, []) or []
    if hasattr(result, key):
        return getattr(result, key) or []
    singular = key[:-1] if key.endswith("s") else key
    if hasattr(result, singular):
        return getattr(result, singular) or []
    return []

def _safe_preview(obj) -> str:
    try:
        if isinstance(obj, dict):
            s = json.dumps(obj, ensure_ascii=False, default=str)
        else:
            s = repr(obj)
    except Exception:
        s = "<unprintable>"
    if len(s) > 4000:
        return s[:4000] + "…"
    return s

def _get_name(obj) -> Optional[str]:
    return getattr(obj, "name", None) or getattr(obj, "title", None)

def _get_artist_name(obj) -> Optional[str]:
    a = getattr(obj, "artist", None)
    if a and hasattr(a, "name"):
        return a.name
    artists = getattr(obj, "artists", None)
    if artists and len(artists) > 0 and hasattr(artists[0], "name"):
        return artists[0].name
    return None

def _get_album_name(obj) -> Optional[str]:
    alb = getattr(obj, "album", None)
    if alb:
        return _get_name(alb)
    return None

def _get_image_url(obj) -> Optional[str]:
    try:
        if hasattr(obj, "image") and callable(getattr(obj, "image")):
            return obj.image(320)
        if hasattr(obj, "image") and not callable(getattr(obj, "image")):
            return obj.image
        if hasattr(obj, "picture"):
            return obj.picture(320, 320)
    except Exception:
        pass
    return None

def _map_track(t) -> TidalItem:
    img = None
    alb = getattr(t, "album", None)
    if alb:
        img = _get_image_url(alb)
    return TidalItem(
        id=int(getattr(t, "id", -1)),
        title=_get_name(t) or "",
        artist=_get_artist_name(t),
        album_name=_get_album_name(t),
        image=img,
    )

def _map_album(a) -> TidalItem:
    return TidalItem(
        id=int(getattr(a, "id", -1)),
        title=_get_name(a) or "",
        artist=_get_artist_name(a),
        album_name=_get_name(a),
        image=_get_image_url(a),
    )

def _map_artist(ar) -> TidalItem:
    return TidalItem(
        id=int(getattr(ar, "id", -1)),
        title=_get_name(ar) or "",
        artist=_get_name(ar),
        album_name=None,
        image=_get_image_url(ar),
    )

@router.get("/search", response_model=SearchResponse)
def search_tidal(
    query: str = Query(..., min_length=1, description="Texto a buscar"),
    type: Literal["track", "album", "artist"] = Query("track", description="Tipo de búsqueda"),
) -> Dict[str, List[TidalItem]]:
    session = refresh_session_if_needed()
    if not session:
        session = get_tidal_session()
    if not session:
        raise HTTPException(status_code=503, detail="Tidal esperando autorización")
    try:
        user_name = _get_user_display_name(session) or "unknown"
        country = _get_country_code(session)
        print(f"[TIDAL] User: {user_name} | Country: {country}", flush=True)
        client_id = None
        try:
            client = getattr(session, "client", None)
            if client is not None:
                client_id = getattr(client, "client_id", None) or getattr(client, "clientId", None)
        except Exception:
            client_id = None
        if not client_id:
            try:
                client_id = getattr(session, "client_id", None) or getattr(session, "clientId", None)
            except Exception:
                client_id = None
        if not client_id:
            client_id = os.getenv("TIDAL_CLIENT_ID")
        client_id = client_id or "unknown"
        try:
            scopes = getattr(session, "scopes", None)
        except Exception:
            scopes = None
        print(f"[TIDAL API CHECK] Usando Client ID: {client_id} | Scopes: {scopes}", flush=True)
        try:
            print(f"[DEBUG] Estado de sesión antes de buscar: {session.check_login()}", flush=True)
        except Exception as ex:
            print(f"[DEBUG] Estado de sesión antes de buscar: error {ex}", flush=True)
        token = getattr(session, "access_token", None)
        if token:
            print(f"[DEBUG] Token actual: {token[:10]}...", flush=True)
        else:
            print("[DEBUG] Token actual: None", flush=True)
        try:
            if not session.check_login():
                logout_tidal_session()
                raise HTTPException(status_code=503, detail="Tidal esperando autorización")
        except HTTPException:
            raise
        except Exception:
            logout_tidal_session()
            raise HTTPException(status_code=503, detail="Tidal esperando autorización")

        models_all = None
        try:
            import tidalapi
            media = getattr(tidalapi, "media", None)
            if media:
                Track = getattr(media, "Track", None)
                Album = getattr(media, "Album", None)
                Artist = getattr(media, "Artist", None)
                models_all = [m for m in (Track, Album, Artist) if m is not None]
        except Exception:
            models_all = None
        result = _search_with_tidalapi(session, query, models=models_all)
        if type == "track":
            items = _extract_items(result, "tracks")
            mapped = [_map_track(t) for t in items]
        elif type == "album":
            items = _extract_items(result, "albums")
            mapped = [_map_album(a) for a in items]
        else:
            items = _extract_items(result, "artists")
            mapped = [_map_artist(ar) for ar in items]
        if len(mapped) == 0:
            try:
                time.sleep(1)
            except Exception:
                pass
            try:
                session.check_login()
            except Exception:
                pass
            try:
                retry = _search_with_tidalapi(session, query, models=models_all)
                if type == "track":
                    mapped = [_map_track(t) for t in _extract_items(retry, "tracks")]
                elif type == "album":
                    mapped = [_map_album(a) for a in _extract_items(retry, "albums")]
                else:
                    mapped = [_map_artist(ar) for ar in _extract_items(retry, "artists")]
                result = retry
            except Exception:
                pass
        if len(mapped) == 0 and type != "track":
            try:
                fallback = _search_with_tidalapi(session, query, models=models_all)
                tracks = _extract_items(fallback, "tracks")
                mapped = [_map_track(t) for t in tracks]
            except Exception:
                pass
        if len(mapped) == 0:
            active = True
            try:
                active = bool(session.check_login())
            except Exception:
                active = True
            print(f"[TIDAL DEBUG] Query: {query} | Session Active: {active} | Region: {country}", flush=True)
            print(f"[TIDAL RAW RESULT] {_safe_preview(result)}", flush=True)
        return {"items": mapped}
    except Exception as e:
        try:
            print(f"[TIDAL SEARCH ERROR] {repr(e)}", flush=True)
        except Exception:
            pass
        try:
            msg = (repr(e) or "").lower()
        except Exception:
            msg = ""
        if "401" in msg or "unauthorized" in msg or "expired" in msg or "token" in msg:
            logout_tidal_session()
            raise HTTPException(status_code=503, detail="Tidal esperando autorización")
        if type != "track":
            try:
                fallback = _search_with_tidalapi(session, query)
                tracks = _extract_items(fallback, "tracks")
                mapped = [_map_track(t) for t in tracks]
                return {"items": mapped}
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me")
def tidal_me() -> Dict[str, Optional[str]]:
    session = get_tidal_session()
    if not session:
        raise HTTPException(status_code=503, detail="Tidal esperando autorización")
    name = _get_user_display_name(session)
    country = _get_country_code(session)
    try:
        print(f"[TIDAL] User: {name or 'unknown'} | Country: {country}", flush=True)
    except Exception:
        pass
    return {"name": name, "country": country}

@router.get("/debug")
def tidal_debug() -> Dict[str, object]:
    session_file_path = "/app/data/tidal_session.json"
    file_exists = Path(session_file_path).exists()
    session = get_tidal_session()
    user_name = _get_user_display_name(session) if session else None
    try:
        scopes_val = getattr(session, "scopes", None) if session else None
    except Exception:
        scopes_val = None
    if scopes_val is None:
        scopes = []
    elif isinstance(scopes_val, (list, tuple, set)):
        scopes = list(scopes_val)
    else:
        scopes = [str(scopes_val)]
    is_logged_in = False
    if session:
        try:
            is_logged_in = bool(session.check_login())
        except Exception:
            is_logged_in = False
    return {
        "is_logged_in": is_logged_in,
        "user_name": user_name,
        "scopes": scopes,
        "session_file_path": session_file_path,
        "session_file_exists": file_exists,
    }

@router.post("/logout")
def tidal_logout() -> Dict[str, str]:
    logout_tidal_session()
    return {"status": "logged_out"}

@router.post("/download", response_model=TidalEnqueueResponse)
def tidal_download(body: TidalDownloadBody, db: Session = Depends(get_db)) -> TidalEnqueueResponse:
    session = get_tidal_session()
    if not session:
        raise HTTPException(status_code=503, detail="Tidal esperando autorización")
    enqueued = 0
    items: List[Dict[str, str]] = []
    if body.type == "track":
        t = None
        try:
            t = session.get_track(body.id)
        except Exception:
            t = None
        title = None
        if t:
            track_title = getattr(t, "name", None) or getattr(t, "title", None)
            album_name = _get_album_name(t)
            artist_name = _get_artist_name(t)
            if track_title and (album_name or artist_name):
                parts = [track_title, album_name or "", artist_name or ""]
                title = " — ".join([p for p in parts if p])
            else:
                title = track_title
        url = f"tidal:track:{body.id}"
        task = DownloadTask(url=url, title=title, status=DownloadStatus.PENDING)
        db.add(task)
        db.commit()
        db.refresh(task)
        tidal_download_track.delay(str(task.id), int(body.id))
        enqueued += 1
        items.append({"id": str(task.id)})
    else:
        try:
            album = session.get_album(body.id)
            tracks = album.tracks(limit=500)
        except Exception as e:
            raise HTTPException(status_code=400, detail="No se pudo obtener el álbum")
        for tr in tracks:
            track_id = int(getattr(tr, "id", -1))
            if track_id <= 0:
                continue
            track_title = getattr(tr, "name", None) or getattr(tr, "title", None)
            artist_name = _get_artist_name(tr)
            album_name = _get_name(album) if 'album' in locals() else None
            title = None
            if track_title and (album_name or artist_name):
                parts = [track_title, album_name or "", artist_name or ""]
                title = " — ".join([p for p in parts if p])
            else:
                title = track_title
            url = f"tidal:track:{track_id}"
            task = DownloadTask(url=url, title=title, status=DownloadStatus.PENDING)
            db.add(task)
            db.commit()
            db.refresh(task)
            tidal_download_track.delay(str(task.id), track_id)
            enqueued += 1
            items.append({"id": str(task.id)})
    return TidalEnqueueResponse(enqueued=enqueued, items=items)

@router.get("/login")
def tidal_login() -> Dict[str, Optional[str]]:
    st = tidal_status()
    if st == "connected":
        return {"status": st, "link": None, "code": None}
    info = start_device_login()
    if not info:
        raise HTTPException(status_code=503, detail="No se pudo iniciar el login de Tidal")
    link, code = info
    return {"status": "awaiting_authorization", "link": link, "code": code}
