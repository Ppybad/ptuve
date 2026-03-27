import json
import os
import threading
from pathlib import Path
from typing import Literal, Optional, Tuple

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None
if load_dotenv:
    load_dotenv()

SESSION_DIR = Path("/app/data")
SESSION_FILE = SESSION_DIR / "tidal_session.json"
LOGIN_LINK_FILE = SESSION_DIR / "LOGIN_LINK.txt"
_CACHED_SESSION = None
_SESSION_LOCK = threading.Lock()

def _scopes_for_tv_app(tidalapi):
    try:
        Scopes = getattr(tidalapi, "Scopes", None) or getattr(tidalapi, "scopes", None)
    except Exception:
        Scopes = None
    desired = ("OFFLINE_CONTROL", "STREAM_HIFI")
    if Scopes is not None:
        vals = []
        for name in desired:
            try:
                v = getattr(Scopes, name, None)
                if v is not None:
                    vals.append(v)
            except Exception:
                continue
        if vals:
            return vals
    return list(desired)

def _create_session(tidalapi):
    client_id = os.getenv("TIDAL_CLIENT_ID")
    client_secret = os.getenv("TIDAL_CLIENT_SECRET")
    if client_id or client_secret:
        kwargs: dict = {}
        if client_id:
            kwargs["client_id"] = client_id
        if client_secret:
            kwargs["client_secret"] = client_secret
        try:
            return tidalapi.Session(**kwargs)
        except TypeError:
            pass
        except Exception:
            pass
    return tidalapi.Session()

def _apply_client_overrides(session) -> None:
    client_id = os.getenv("TIDAL_CLIENT_ID")
    client_secret = os.getenv("TIDAL_CLIENT_SECRET")
    if not client_id and not client_secret:
        return
    try:
        client = getattr(session, "client", None)
        if client is not None:
            if client_id and hasattr(client, "client_id"):
                setattr(client, "client_id", client_id)
            if client_secret and hasattr(client, "client_secret"):
                setattr(client, "client_secret", client_secret)
    except Exception:
        pass
    try:
        if client_id and hasattr(session, "client_id"):
            setattr(session, "client_id", client_id)
        if client_secret and hasattr(session, "client_secret"):
            setattr(session, "client_secret", client_secret)
    except Exception:
        pass

def _session_has_empty_scopes(session) -> bool:
    try:
        scopes_val = getattr(session, "scopes", None)
    except Exception:
        scopes_val = None
    if isinstance(scopes_val, (list, tuple, set)) and len(scopes_val) == 0:
        return True
    return False

def _save_session(session) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "token_type": getattr(session, "token_type", None),
        "access_token": getattr(session, "access_token", None),
        "refresh_token": getattr(session, "refresh_token", None),
        "expiry_time": getattr(session, "expiry_time", None),
        "client_id": os.getenv("TIDAL_CLIENT_ID") or getattr(session, "client_id", None) or None,
    }
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def _delete_saved_session_file() -> None:
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
    except Exception:
        pass

def _get_saved_client_id() -> Optional[str]:
    if not SESSION_FILE.exists():
        return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cid = data.get("client_id")
        return cid
    except Exception:
        return None

def _purge_if_client_changed() -> None:
    env_id = os.getenv("TIDAL_CLIENT_ID")
    saved = _get_saved_client_id()
    if env_id and saved and env_id != saved:
        _delete_saved_session_file()

def _is_auth_error(err: Exception) -> bool:
    try:
        msg = (repr(err) or "").lower()
    except Exception:
        msg = ""
    for token in ("401", "unauthorized", "forbidden", "token", "expired", "invalid_grant"):
        if token in msg:
            return True
    return False

def _load_session_into(session) -> bool:
    if not SESSION_FILE.exists():
        return False
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        token_type = data.get("token_type")
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expiry_time = data.get("expiry_time")
        if token_type and access_token and expiry_time is not None:
            ok = session.load_oauth_session(token_type, access_token, refresh_token, expiry_time)
            return bool(ok)
        return False
    except Exception:
        return False

def _write_login_link(text: str) -> None:
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOGIN_LINK_FILE, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass

def ensure_session_and_start_device_login_if_needed(printer=print) -> Literal["connected", "awaiting_authorization"]:
    global _CACHED_SESSION
    try:
        import tidalapi
    except Exception as e:
        print(f"Tidal no disponible: {e}", flush=True)
        try:
            printer(f"Tidal no disponible: {e}")
        except Exception:
            pass
        return "awaiting_authorization"
    with _SESSION_LOCK:
        if _CACHED_SESSION is None:
            _CACHED_SESSION = _create_session(tidalapi)
        session = _CACHED_SESSION
    _apply_client_overrides(session)
    _purge_if_client_changed()
    if _load_session_into(session):
        if _session_has_empty_scopes(session):
            _delete_saved_session_file()
        else:
            return "connected"
    try:
        login = None
        future = None
        if hasattr(session, "login_oauth_device"):
            scopes = _scopes_for_tv_app(tidalapi)
            try:
                login, future = session.login_oauth_device(scopes=scopes)
            except TypeError:
                try:
                    login, future = session.login_oauth_device(scopes)
                except Exception:
                    login, future = session.login_oauth_device()
        elif hasattr(session, "login_oauth"):
            scopes = _scopes_for_tv_app(tidalapi)
            try:
                login, future = session.login_oauth(scopes=scopes)
            except TypeError:
                try:
                    login, future = session.login_oauth(scopes)
                except Exception:
                    login, future = session.login_oauth()
        else:
            return "awaiting_authorization"
        try:
            uri_complete = getattr(login, "verification_uri_complete", None)
            uri = getattr(login, "verification_uri", None)
            code = getattr(login, "user_code", None)
            if uri_complete:
                msg = f"Tidal: abre {uri_complete}"
                print(msg, flush=True)
                try:
                    printer(msg)
                except Exception:
                    pass
                _write_login_link(uri_complete)
            elif uri and code:
                msg = f"Tidal: visita {uri} y usa el código {code}"
                print(msg, flush=True)
                try:
                    printer(msg)
                except Exception:
                    pass
                _write_login_link(f"{uri} {code}")
            elif uri:
                msg = f"Tidal: visita {uri}"
                print(msg, flush=True)
                try:
                    printer(msg)
                except Exception:
                    pass
                _write_login_link(uri)
        except Exception:
            pass
        def _wait_and_persist():
            try:
                future.result()
                try:
                    if hasattr(session, "save_session"):
                        session.save_session(str(SESSION_FILE))
                    else:
                        _save_session(session)
                    print(f"[TIDAL] Sesión guardada físicamente en {SESSION_FILE}", flush=True)
                except Exception as ex:
                    print(f"[TIDAL] Error guardando sesión: {ex}", flush=True)
                    _save_session(session)
                    print(f"[TIDAL] Sesión guardada físicamente en {SESSION_FILE}", flush=True)
                global _CACHED_SESSION
                _CACHED_SESSION = session
                try:
                    printer(f"[TIDAL] Sesión guardada físicamente en {SESSION_FILE}")
                except Exception:
                    pass
            except Exception as ex:
                print(f"Tidal: error de autorización: {ex}", flush=True)
                try:
                    printer(f"Tidal: error de autorización: {ex}")
                except Exception:
                    pass
        threading.Thread(target=_wait_and_persist, daemon=True).start()
        return "awaiting_authorization"
    except Exception as e:
        print(f"Tidal: error iniciando dispositivo: {e}", flush=True)
        try:
            printer(f"Tidal: error iniciando dispositivo: {e}")
        except Exception:
            pass
        return "awaiting_authorization"

def tidal_status() -> Literal["connected", "awaiting_authorization"]:
    global _CACHED_SESSION
    if not SESSION_FILE.exists():
        _CACHED_SESSION = None
        return "awaiting_authorization"
    if _CACHED_SESSION is not None:
        try:
            if _session_has_empty_scopes(_CACHED_SESSION):
                _CACHED_SESSION = None
                _delete_saved_session_file()
                return "awaiting_authorization"
            if _CACHED_SESSION.check_login():
                return "connected"
            _CACHED_SESSION = None
            _delete_saved_session_file()
            return "awaiting_authorization"
        except Exception as ex:
            if _is_auth_error(ex):
                _CACHED_SESSION = None
                _delete_saved_session_file()
                return "awaiting_authorization"
            return "connected"
    return "connected" if refresh_session_if_needed() else "awaiting_authorization"

def get_tidal_session():
    global _CACHED_SESSION
    try:
        import tidalapi
    except Exception:
        return None
    with _SESSION_LOCK:
        if _CACHED_SESSION is None:
            _CACHED_SESSION = _create_session(tidalapi)
        session = _CACHED_SESSION
    _apply_client_overrides(session)
    _purge_if_client_changed()
    if _load_session_into(session):
        if _session_has_empty_scopes(session):
            _delete_saved_session_file()
            return None
        return session
    return session if getattr(session, "access_token", None) else None

def logout_tidal_session() -> None:
    global _CACHED_SESSION
    with _SESSION_LOCK:
        _CACHED_SESSION = None
    _delete_saved_session_file()

def refresh_session_if_needed():
    session = get_tidal_session()
    if not session:
        return None
    try:
        ok = session.check_login()
        if ok:
            return session
        logout_tidal_session()
        return None
    except Exception as ex:
        if _is_auth_error(ex):
            logout_tidal_session()
            return None
        return session

def start_device_login() -> Optional[Tuple[str, Optional[str]]]:
    try:
        import tidalapi
    except Exception:
        return None
    global _CACHED_SESSION
    with _SESSION_LOCK:
        if _CACHED_SESSION is None:
            _CACHED_SESSION = _create_session(tidalapi)
        session = _CACHED_SESSION
    _apply_client_overrides(session)
    _purge_if_client_changed()
    if _load_session_into(session):
        if not _session_has_empty_scopes(session):
            return None
        _delete_saved_session_file()
    try:
        login = None
        future = None
        if hasattr(session, "login_oauth_device"):
            scopes = _scopes_for_tv_app(tidalapi)
            try:
                login, future = session.login_oauth_device(scopes=scopes)
            except TypeError:
                try:
                    login, future = session.login_oauth_device(scopes)
                except Exception:
                    login, future = session.login_oauth_device()
        elif hasattr(session, "login_oauth"):
            scopes = _scopes_for_tv_app(tidalapi)
            try:
                login, future = session.login_oauth(scopes=scopes)
            except TypeError:
                try:
                    login, future = session.login_oauth(scopes)
                except Exception:
                    login, future = session.login_oauth()
        else:
            return None
        uri_complete = getattr(login, "verification_uri_complete", None)
        uri = getattr(login, "verification_uri", None)
        code = getattr(login, "user_code", None)
        if uri_complete:
            print(f"Tidal: abre {uri_complete}", flush=True)
            _write_login_link(uri_complete)
        elif uri and code:
            print(f"Tidal: visita {uri} y usa el código {code}", flush=True)
            _write_login_link(f"{uri} {code}")
        elif uri:
            print(f"Tidal: visita {uri}", flush=True)
            _write_login_link(uri)
        def _wait_and_persist():
            try:
                future.result()
                try:
                    if hasattr(session, "save_session"):
                        session.save_session(str(SESSION_FILE))
                    else:
                        _save_session(session)
                    print(f"[TIDAL] Sesión guardada físicamente en {SESSION_FILE}", flush=True)
                except Exception as ex:
                    print(f"[TIDAL] Error guardando sesión: {ex}", flush=True)
                    _save_session(session)
                    print(f"[TIDAL] Sesión guardada físicamente en {SESSION_FILE}", flush=True)
                global _CACHED_SESSION
                _CACHED_SESSION = session
            except Exception as ex:
                print(f"Tidal: error de autorización: {ex}", flush=True)
        threading.Thread(target=_wait_and_persist, daemon=True).start()
        if uri_complete:
            return (uri_complete, None)
        if uri:
            return (uri, code)
        return None
    except Exception:
        return None
