from typing import List, Literal, Optional, Dict
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.core.tidal_auth import get_tidal_session, tidal_status, start_device_login
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
    session = get_tidal_session()
    if not session:
        raise HTTPException(status_code=503, detail="Tidal esperando autorización")
    try:
        result = session.search(query=query)
        if type == "track":
            items = result.get("tracks", []) or []
            mapped = [_map_track(t) for t in items]
        elif type == "album":
            items = result.get("albums", []) or []
            mapped = [_map_album(a) for a in items]
        else:
            items = result.get("artists", []) or []
            mapped = [_map_artist(ar) for ar in items]
        return {"items": mapped}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
