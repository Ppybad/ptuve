import os
import uuid
import subprocess
from typing import Optional, List
from backend.app.core.celery_app import celery_app
from backend.app.core.database import SessionLocal
from backend.app.models.download import DownloadTask, DownloadStatus
from backend.app.core.config import settings
from backend.app.core.tidal_auth import get_tidal_session

def _find_new_file(before: set, folder: str, exts: List[str]) -> Optional[str]:
    after = set(os.listdir(folder))
    created = [f for f in (after - before) if any(f.lower().endswith(ext) for ext in exts)]
    if not created:
        # fallback: guess most recent by mtime
        candidates = [os.path.join(folder, f) for f in after]
        if not candidates:
            return None
        candidates = [p for p in candidates if os.path.isfile(p)]
        if not candidates:
            return None
        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return candidates[0]
    return os.path.join(folder, created[0])

def _fmt_lrc_time(hours: int, minutes: int, seconds: int, millis: int) -> str:
    total_minutes = hours * 60 + minutes
    centis = int(round(millis / 10.0))
    return f"[{total_minutes:02d}:{seconds:02d}.{centis:02d}]"

def _parse_time_to_lrc(ts: str) -> Optional[str]:
    try:
        if "," in ts:  # SRT hh:mm:ss,ms
            hms, ms = ts.split(",")
            parts = hms.split(":")
            if len(parts) == 3:
                h, m, s = map(int, parts)
            else:
                h = 0
                m, s = map(int, parts)
            return _fmt_lrc_time(h, m, s, int(ms))
        else:  # VTT hh:mm:ss.mmm or mm:ss.mmm
            hms, ms = ts.split(".")
            parts = hms.split(":")
            if len(parts) == 3:
                h, m, s = map(int, parts)
            else:
                h = 0
                m, s = map(int, parts)
            return _fmt_lrc_time(h, m, s, int(ms[:3]))
    except Exception:
        return None

def _convert_subs_to_lrc(sub_path: str, lrc_path: str) -> bool:
    try:
        with open(sub_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [ln.rstrip("\n\r") for ln in f.readlines()]
        is_vtt = sub_path.lower().endswith(".vtt")
        is_srt = sub_path.lower().endswith(".srt")
        if not (is_vtt or is_srt):
            return False
        lrc_lines: List[str] = []
        if is_vtt:
            content = []
            for ln in lines:
                if ln.strip().upper().startswith("WEBVTT") or ln.strip().upper().startswith("NOTE"):
                    continue
                content.append(ln)
            i = 0
            while i < len(content):
                ln = content[i].strip()
                if "-->" in ln:
                    try:
                        start, _end = [p.strip() for p in ln.split("-->")]
                        tag = _parse_time_to_lrc(start)
                        text_parts = []
                        j = i + 1
                        while j < len(content) and content[j].strip() and "-->" not in content[j]:
                            text_parts.append(content[j].strip())
                            j += 1
                        text = " ".join(text_parts).strip()
                        if tag and text:
                            lrc_lines.append(f"{tag}{text}")
                        i = j
                    except Exception:
                        i += 1
                else:
                    i += 1
        else:
            blocks = []
            block = []
            for ln in lines:
                if ln.strip() == "":
                    if block:
                        blocks.append(block)
                        block = []
                else:
                    block.append(ln)
            if block:
                blocks.append(block)
            for b in blocks:
                time_line = None
                text_lines = []
                for ln in b:
                    if "-->" in ln and time_line is None:
                        time_line = ln
                    elif time_line is not None:
                        text_lines.append(ln.strip())
                if time_line:
                    try:
                        start, _end = [p.strip() for p in time_line.split("-->")]
                        tag = _parse_time_to_lrc(start)
                        text = " ".join(text_lines).strip()
                        if tag and text:
                            lrc_lines.append(f"{tag}{text}")
                    except Exception:
                        continue
        if not lrc_lines:
            return False
        with open(lrc_path, "w", encoding="utf-8") as out:
            out.write("\n".join(lrc_lines))
        return True
    except Exception:
        return False

@celery_app.task(name="tidal_download_track")
def tidal_download_track(task_id: str, track_id: int) -> None:
    db = SessionLocal()
    try:
        uid = uuid.UUID(task_id)
        task: Optional[DownloadTask] = db.get(DownloadTask, uid)
        if not task:
            return
        task.status = DownloadStatus.PROCESSING
        db.add(task)
        db.commit()
        db.refresh(task)
        session = get_tidal_session()
        if not session:
            task.status = DownloadStatus.FAILED
            db.add(task)
            db.commit()
            return
        try:
            t = session.get_track(track_id)
        except Exception:
            t = None
        artist_name = None
        album_name = None
        title = None
        year_str = None
        url = f"https://listen.tidal.com/track/{track_id}"
        if t is not None:
            title = getattr(t, "name", None) or getattr(t, "title", None)
            if hasattr(t, "artist") and t.artist and hasattr(t.artist, "name"):
                artist_name = t.artist.name
            elif hasattr(t, "artists") and t.artists and hasattr(t.artists[0], "name"):
                artist_name = t.artists[0].name
            if hasattr(t, "album") and t.album:
                album_name = getattr(t.album, "name", None) or getattr(t.album, "title", None)
                if hasattr(t.album, "available_release_date") and t.album.available_release_date:
                    year_str = str(getattr(t.album.available_release_date, "year", None) or "")
            share = getattr(t, "listen_url", None) or getattr(t, "share_url", None)
            if share:
                url = share
        out_dir = settings.downloads_dir
        os.makedirs(out_dir, exist_ok=True)
        try:
            os.chmod(out_dir, 0o777)
        except Exception:
            pass
        template = os.path.join(out_dir, "%(title)s.%(ext)s")
        before = set(os.listdir(out_dir))
        access_token = getattr(session, "access_token", None)
        if access_token:
            print(f"[DOWNLOAD DEBUG] Iniciando descarga de track {track_id} con token {access_token[:10]}....", flush=True)
        else:
            print(f"[DOWNLOAD DEBUG] Iniciando descarga de track {track_id} con token None", flush=True)
        cmd: List[str] = [
            "yt-dlp",
            "-x",
            "--audio-format",
            "flac",
            "--write-subs",
            "--sub-langs",
            "all",
            "--embed-metadata",
            "--embed-thumbnail",
            "--add-metadata",
        ]
        if access_token:
            cmd += ["--add-header", f"Authorization: Bearer {access_token}"]
        cmd += ["-o", template, url]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            task.status = DownloadStatus.FAILED
            db.add(task)
            db.commit()
            return
        if res.returncode != 0:
            task.status = DownloadStatus.FAILED
            db.add(task)
            db.commit()
            return
        file_path = _find_new_file(before, out_dir, [".flac"])
        if file_path:
            task.status = DownloadStatus.COMPLETED
            task.file_path = file_path
            if not task.title:
                task.title = title or os.path.splitext(os.path.basename(file_path))[0]
            try:
                try:
                    base = os.path.splitext(file_path)[0]
                    folder = os.path.dirname(file_path)
                    subs = []
                    for f in os.listdir(folder):
                        if f.startswith(os.path.basename(base) + ".") and (f.lower().endswith(".vtt") or f.lower().endswith(".srt")):
                            subs.append(os.path.join(folder, f))
                    lrc_path = base + ".lrc"
                    converted = False
                    for sp in subs:
                        if _convert_subs_to_lrc(sp, lrc_path):
                            converted = True
                            try:
                                os.remove(sp)
                            except OSError:
                                pass
                            break
                    if not converted:
                        import syncedlyrics as sdl
                        query = " ".join([p for p in [title, artist_name] if p])
                        if query:
                            lrc = sdl.search(query, synced_only=False)
                            if lrc:
                                with open(lrc_path, "w", encoding="utf-8") as f:
                                    f.write(lrc)
                except Exception:
                    pass
            except Exception:
                pass
        else:
            task.status = DownloadStatus.FAILED
        db.add(task)
        db.commit()
    finally:
        db.close()
