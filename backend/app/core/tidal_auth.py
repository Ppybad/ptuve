import json
import os
import threading
from pathlib import Path
from typing import Literal, Optional, Tuple

SESSION_DIR = Path("/app/data")
SESSION_FILE = SESSION_DIR / "tidal_session.json"
LOGIN_LINK_FILE = SESSION_DIR / "LOGIN_LINK.txt"

def _save_session(session) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "token_type": getattr(session, "token_type", None),
        "access_token": getattr(session, "access_token", None),
        "refresh_token": getattr(session, "refresh_token", None),
        "expiry_time": getattr(session, "expiry_time", None),
    }
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

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
    try:
        import tidalapi
    except Exception as e:
        print(f"Tidal no disponible: {e}", flush=True)
        try:
            printer(f"Tidal no disponible: {e}")
        except Exception:
            pass
        return "awaiting_authorization"
    session = tidalapi.Session()
    if _load_session_into(session):
        return "connected"
    try:
        login = None
        future = None
        if hasattr(session, "login_oauth_device"):
            login, future = session.login_oauth_device()
        elif hasattr(session, "login_oauth"):
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
                _save_session(session)
                print("Tidal: sesión almacenada", flush=True)
                try:
                    printer("Tidal: sesión almacenada")
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
    return "connected" if SESSION_FILE.exists() else "awaiting_authorization"

def get_tidal_session():
    try:
        import tidalapi
    except Exception:
        return None
    session = tidalapi.Session()
    if _load_session_into(session):
        try:
            ok = session.check_login()
            if ok:
                return session
        except Exception:
            return session
    return None

def start_device_login() -> Optional[Tuple[str, Optional[str]]]:
    try:
        import tidalapi
    except Exception:
        return None
    session = tidalapi.Session()
    if _load_session_into(session):
        return None
    try:
        login = None
        future = None
        if hasattr(session, "login_oauth_device"):
            login, future = session.login_oauth_device()
        elif hasattr(session, "login_oauth"):
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
                _save_session(session)
                print("Tidal: sesión almacenada", flush=True)
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
