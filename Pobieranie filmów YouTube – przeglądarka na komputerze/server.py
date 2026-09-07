#!/usr/bin/env python3
"""Lokalny serwer WWW dla pobieracza filmów z YouTube.

Uruchamia mały serwer Flask na 127.0.0.1, wystawia stronę index.html
(w folderze static/) i proste API, które w tle korzysta z yt-dlp do
pobierania filmów. Przy starcie automatycznie otwiera przeglądarkę.
"""

import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser
import zipfile

from flask import Flask, jsonify, request, send_from_directory

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


# Bez srodowiska JavaScript (Deno) domyslny klient "web" YouTube bywa
# zepsuty ("This video is not available"). yt-dlp pobiera formaty ze
# wszystkich wymienionych klientow i laczy wyniki, wiec dodanie
# android/ios/tv ratuje stare/problematyczne filmy, nie psujac zwyklych.
YT_PLAYER_CLIENTS = ["default", "android", "ios", "tv", "web_safari"]

_VIMEO_ID_RE = re.compile(r"^https?://(?:www\.)?vimeo\.com/(\d+)(?:[/?#]|$)")

TOOLS_DIR = os.path.join(os.path.expanduser("~"), ".yt_downloader_tools")

# Od 2025 r. YouTube wymaga rozwiazywania podpisow w JavaScript. yt-dlp robi
# to przez zewnetrzny silnik (EJS) uruchamiany w Deno. Bez tego dostepny jest
# tylko format 18 (360p). Binarke Deno pobieramy raz, przy pierwszym uruchomieniu.
DENO_ASSETS = {
    ("Windows", "AMD64"): "deno-x86_64-pc-windows-msvc.zip",
    ("Windows", "ARM64"): "deno-aarch64-pc-windows-msvc.zip",
    ("Darwin", "arm64"): "deno-aarch64-apple-darwin.zip",
    ("Darwin", "x86_64"): "deno-x86_64-apple-darwin.zip",
    ("Linux", "x86_64"): "deno-x86_64-unknown-linux-gnu.zip",
    ("Linux", "aarch64"): "deno-aarch64-unknown-linux-gnu.zip",
}

_ffmpeg_cache = {}
_deno_cache = {}


def _add_to_path(directory):
    if directory and directory not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")


def ensure_deno():
    """Zwraca sciezke do 'deno' albo None. Pobiera binarke przy pierwszym uzyciu."""
    if "path" in _deno_cache:
        return _deno_cache["path"]

    found = shutil.which("deno")
    if found:
        _deno_cache["path"] = found
        return found

    exe = "deno.exe" if os.name == "nt" else "deno"
    dest_dir = os.path.join(TOOLS_DIR, "deno")
    dest = os.path.join(dest_dir, exe)
    if os.path.exists(dest):
        _add_to_path(dest_dir)
        _deno_cache["path"] = dest
        return dest

    asset = DENO_ASSETS.get((platform.system(), platform.machine()))
    if not asset:
        _deno_cache["path"] = None
        return None

    url = f"https://github.com/denoland/deno/releases/latest/download/{asset}"
    try:
        os.makedirs(dest_dir, exist_ok=True)
        tmp = dest + ".zip"
        urllib.request.urlretrieve(url, tmp)
        with zipfile.ZipFile(tmp) as archive:
            archive.extractall(dest_dir)
        os.remove(tmp)
        if os.name != "nt":
            os.chmod(dest, 0o755)
        _add_to_path(dest_dir)
        _deno_cache["path"] = dest
        return dest
    except Exception:
        _deno_cache["path"] = None
        return None


def base_extractor_args():
    return {"youtube": {"player_client": list(YT_PLAYER_CLIENTS)}}


def apply_youtube_runtime(ydl_opts):
    """Wlacza silnik JS (Deno + EJS), jesli dostepny - inaczej YouTube oddaje
    tylko 360p. Zwraca True, gdy silnik jest gotowy."""
    if ensure_deno():
        ydl_opts["remote_components"] = ["ejs:github"]
        return True
    return False


def vimeo_embed_fallback(url, exc):
    """Dla publicznych, osadzalnych filmow Vimeo, ktore od niedawna wymagaja
    logowania na vimeo.com, sprobuj adresu player.vimeo.com."""
    match = _VIMEO_ID_RE.match(url or "")
    if match and "logged-in" in str(exc).lower():
        return f"https://player.vimeo.com/video/{match.group(1)}"
    return None


def resolve_ffmpeg():
    """Zwraca (location, has_ffprobe).

    location: katalog z ffmpeg+ffprobe (preferowane) albo sciezka do samego
    ffmpeg (fallback z imageio-ffmpeg, bez ffprobe). yt-dlp potrzebuje ffprobe
    (lub AtomicParsley), zeby osadzic miniaturke w pliku mp4/m4a.
    """
    if _ffmpeg_cache:
        return _ffmpeg_cache["location"], _ffmpeg_cache["has_ffprobe"]

    # 1. static-ffmpeg dostarcza ZAROWNO ffmpeg jak i ffprobe (pobiera przy
    #    pierwszym uzyciu i dopisuje do PATH).
    try:
        import static_ffmpeg

        try:
            static_ffmpeg.add_paths(weak=True)
        except TypeError:
            static_ffmpeg.add_paths()
    except Exception:
        pass

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        _ffmpeg_cache.update(location=os.path.dirname(ffmpeg), has_ffprobe=True)
        return _ffmpeg_cache["location"], True

    # 2. imageio-ffmpeg: tylko ffmpeg, brak ffprobe.
    if imageio_ffmpeg is not None:
        try:
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            _ffmpeg_cache.update(location=exe, has_ffprobe=bool(ffprobe))
            return exe, bool(ffprobe)
        except Exception:
            pass

    if ffmpeg:
        _ffmpeg_cache.update(location=os.path.dirname(ffmpeg), has_ffprobe=bool(ffprobe))
        return _ffmpeg_cache["location"], bool(ffprobe)

    _ffmpeg_cache.update(location=None, has_ffprobe=False)
    return None, False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "Pobrane_filmy")
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".yt_downloader_web_config.json")

QUALITY_FORMATS = {
    "best": "bv*+ba/b",
    "1080p": "bv*[height<=1080]+ba/b",
    "720p": "bv*[height<=720]+ba/b",
    "480p": "bv*[height<=480]+ba/b",
    "audio": "audio",
}


def quality_to_format(quality):
    """Zamienia wartosc z listy jakosci na selektor formatu yt-dlp.

    Obsluguje predefiniowane klucze oraz dowolne '<liczba>p' (np. '1440p'),
    ktore moga przyjsc z dynamicznej listy po sprawdzeniu linku.
    """
    quality = (quality or "best").strip().lower()
    if quality in QUALITY_FORMATS:
        return QUALITY_FORMATS[quality]
    if quality.endswith("p") and quality[:-1].isdigit():
        return f"bv*[height<={quality[:-1]}]+ba/b"
    return QUALITY_FORMATS["best"]


DEFAULT_CONFIG = {
    "quality": "best",
    "browser": "none",
    "output_dir": DEFAULT_OUTPUT_DIR,
    "subtitles": False,
    "sub_langs": "pl,en",
    "embed_metadata": True,
    "playlist": False,
    "playlist_range": "",
}

PICK_FOLDER_SCRIPT = r"""
import sys
import tkinter as tk
from tkinter import filedialog
initial = sys.argv[1] if len(sys.argv) > 1 else ""
root = tk.Tk()
root.withdraw()
try:
    root.attributes("-topmost", True)
except Exception:
    pass
path = filedialog.askdirectory(initialdir=initial or None)
print(path)
"""

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

jobs = {}
jobs_lock = threading.Lock()


def load_config():
    config = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    except Exception:
        pass
    return config


def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def pick_folder(initial_dir):
    try:
        result = subprocess.run(
            [sys.executable, "-c", PICK_FOLDER_SCRIPT, initial_dir or ""],
            capture_output=True, text=True, timeout=120,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _job_log(job_id, message):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is not None:
            job["log"].append(message)


def _set_item_status(job_id, index, status_text):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is not None and 0 <= index < len(job["items"]):
            job["items"][index]["status"] = status_text


_MEDIA_EXTS = (".mp4", ".mkv", ".webm", ".mp3", ".m4a", ".opus", ".flac", ".mov")
_THUMB_EXTS = (".webp", ".png", ".jpg", ".jpeg")


def _cleanup_stray_files(output_dir):
    """Sprzata pliki tymczasowe i osierocone miniaturki po pobraniu."""
    try:
        for path in glob.glob(os.path.join(glob.escape(output_dir), "*")):
            lower = path.lower()
            if lower.endswith((".part", ".ytdl", ".temp")) or ".part-" in lower:
                _safe_remove(path)
                continue
            stem, ext = os.path.splitext(path)
            if ext.lower() in _THUMB_EXTS and any(
                os.path.exists(stem + media) for media in _MEDIA_EXTS
            ):
                _safe_remove(path)
    except Exception:
        pass


def _safe_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def _run_download(job_id, urls, settings):
    format_selector = quality_to_format(settings.get("quality", "best"))
    output_dir = settings["output_dir"]
    ffmpeg_location, has_ffprobe = resolve_ffmpeg()

    ydl_opts = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "ignoreerrors": True,
        "progress_hooks": [lambda d: _progress_hook(job_id, d)],
        "socket_timeout": 30,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_args": base_extractor_args(),
    }
    if not apply_youtube_runtime(ydl_opts):
        _job_log(job_id, "Uwaga: brak środowiska Deno — YouTube może oddać "
                         "tylko 360p. Uruchom ponownie z dostępem do internetu.")

    is_audio = format_selector == "audio"
    if is_audio:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        ydl_opts["format"] = format_selector
        ydl_opts["merge_output_format"] = "mp4"

    if settings.get("subtitles"):
        langs = [lang.strip() for lang in settings.get("sub_langs", "").split(",") if lang.strip()] or ["pl", "en"]
        ydl_opts["writesubtitles"] = True
        ydl_opts["writeautomaticsub"] = True
        ydl_opts["subtitleslangs"] = langs
        if not is_audio:
            ydl_opts["embedsubtitles"] = True

    if settings.get("embed_metadata"):
        ydl_opts.setdefault("postprocessors", [])
        ydl_opts["postprocessors"] += [{"key": "FFmpegMetadata"}]
        # Osadzenie miniaturki w mp4/m4a wymaga ffprobe (albo AtomicParsley).
        # Dla mp3 wystarcza mutagen. Bez tego yt-dlp konczy z bledem i
        # zostawia obok pliku smieciowe .webp/.png, wiec pomijamy krok.
        if has_ffprobe or is_audio:
            ydl_opts["writethumbnail"] = True
            ydl_opts["postprocessors"] += [{"key": "EmbedThumbnail"}]
        else:
            _job_log(
                job_id,
                "Uwaga: pomijam osadzanie miniaturki (brak ffprobe). "
                "Zainstaluj zaleznosci ponownie (static-ffmpeg) albo AtomicParsley.",
            )

    if settings.get("playlist"):
        ydl_opts["noplaylist"] = False
        if settings.get("playlist_range"):
            ydl_opts["playlist_items"] = settings["playlist_range"]
    else:
        ydl_opts["noplaylist"] = True

    if ffmpeg_location:
        ydl_opts["ffmpeg_location"] = ffmpeg_location

    browser = settings.get("browser")
    if browser and browser != "none":
        ydl_opts["cookiesfrombrowser"] = (browser,)

    had_error = False
    try:
        os.makedirs(output_dir, exist_ok=True)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for i, url in enumerate(urls):
                _set_item_status(job_id, i, "downloading")
                _job_log(job_id, f"Rozpoczynam: {url}")
                try:
                    ydl.download([url])
                    _set_item_status(job_id, i, "done")
                except Exception as exc:
                    alt = vimeo_embed_fallback(url, exc)
                    if alt:
                        try:
                            _job_log(job_id, f"Vimeo wymaga logowania — próbuję: {alt}")
                            ydl.download([alt])
                            _set_item_status(job_id, i, "done")
                            continue
                        except Exception as exc2:
                            exc = exc2
                    had_error = True
                    _set_item_status(job_id, i, "error")
                    _job_log(job_id, f"Błąd przy pobieraniu {url}: {exc}")
    except Exception as exc:
        had_error = True
        _job_log(job_id, f"Nieoczekiwany błąd: {exc}")

    _cleanup_stray_files(output_dir)

    with jobs_lock:
        job = jobs.get(job_id)
        if job is not None:
            job["status"] = "error" if had_error else "finished"
            if had_error:
                job["log"].append(
                    "Zakończono z błędami. Jeśli film jest prywatny/niepubliczny, wybierz "
                    "przeglądarkę w polu 'Ciasteczka z przeglądarki' (musisz być zalogowany "
                    "w tej przeglądarce na koncie z dostępem do filmu)."
                )
            else:
                job["log"].append("Gotowe! Pliki zapisane w: " + output_dir)


def _progress_hook(job_id, d):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                job["percent"] = downloaded / total * 100
            job["current_file"] = os.path.basename(d.get("filename", ""))
        elif d.get("status") == "finished":
            job["log"].append(f"Pobrano, przetwarzanie: {os.path.basename(d.get('filename', ''))}")


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/config")
def get_config():
    return jsonify(load_config())


@app.route("/api/pick-folder", methods=["POST"])
def pick_folder_route():
    data = request.get_json(force=True) or {}
    initial_dir = data.get("initial_dir") or DEFAULT_OUTPUT_DIR
    path = pick_folder(initial_dir)
    if path:
        return jsonify({"path": path})
    return jsonify({"path": "", "error": "Nie wybrano folderu albo okno dialogowe jest niedostępne na tym systemie."})


def _probe_url(url):
    ffmpeg_location, _ = resolve_ffmpeg()
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "extractor_args": base_extractor_args(),
    }
    apply_youtube_runtime(opts)
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        alt = vimeo_embed_fallback(url, exc)
        if not alt:
            raise
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(alt, download=False)
        except Exception:
            raise exc

    if info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if e]
        return {
            "url": url,
            "playlist": True,
            "title": info.get("title") or "Playlista",
            "count": len(entries),
            "heights": [],
        }

    heights = sorted(
        {f["height"] for f in info.get("formats", []) if f.get("height")},
        reverse=True,
    )
    has_audio = any(
        f.get("acodec") and f.get("acodec") != "none" for f in info.get("formats", [])
    )
    return {
        "url": url,
        "playlist": False,
        "title": info.get("title") or url,
        "uploader": info.get("uploader") or info.get("channel") or "",
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "heights": heights,
        "has_audio": has_audio,
    }


@app.route("/api/probe", methods=["POST"])
def probe():
    if yt_dlp is None:
        return jsonify({"error": "Biblioteka yt-dlp nie jest zainstalowana."}), 500

    data = request.get_json(force=True) or {}
    urls = [u.strip() for u in data.get("urls", []) if u.strip()]
    if not urls:
        return jsonify({"error": "Podaj przynajmniej jeden link."}), 400

    results = []
    for url in urls:
        try:
            results.append(_probe_url(url))
        except Exception as exc:
            results.append({"url": url, "error": _friendly_error(exc)})
    return jsonify({"results": results})


def _friendly_error(exc):
    msg = str(exc)
    low = msg.lower()
    if "this video is not available" in low or "page needs to be reloaded" in low:
        return (msg + "  —  Wskazówka: to zwykle brak środowiska JavaScript. "
                "Zainstaluj Deno (deno.com) i dodaj do PATH, albo wybierz "
                "przeglądarkę w polu „Ciasteczka z przeglądarki”.")
    if "logged-in" in low or "cookies" in low or "sign in" in low:
        return (msg + "  —  Wskazówka: ustaw pole „Ciasteczka z przeglądarki” "
                "na przeglądarkę, w której jesteś zalogowany na tym serwisie.")
    return msg


@app.route("/api/download", methods=["POST"])
def start_download():
    if yt_dlp is None:
        return jsonify({"error": "Biblioteka yt-dlp nie jest zainstalowana."}), 500

    data = request.get_json(force=True) or {}
    urls = [u.strip() for u in data.get("urls", []) if u.strip()]
    if not urls:
        return jsonify({"error": "Podaj przynajmniej jeden link."}), 400

    settings = {
        "quality": data.get("quality", "best"),
        "browser": data.get("browser", "none"),
        "output_dir": data.get("output_dir") or DEFAULT_OUTPUT_DIR,
        "subtitles": bool(data.get("subtitles", False)),
        "sub_langs": data.get("sub_langs") or "pl,en",
        "embed_metadata": bool(data.get("embed_metadata", True)),
        "playlist": bool(data.get("playlist", False)),
        "playlist_range": data.get("playlist_range", ""),
    }
    save_config(settings)

    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {
            "status": "downloading",
            "percent": 0,
            "current_file": "",
            "log": [],
            "items": [{"url": u, "status": "queued"} for u in urls],
            "created": time.time(),
        }

    thread = threading.Thread(target=_run_download, args=(job_id, urls, settings), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return jsonify({"error": "Nieznane zadanie."}), 404
        return jsonify({
            "status": job["status"],
            "percent": job["percent"],
            "current_file": job["current_file"],
            "log": job["log"],
            "items": job["items"],
        })


def _open_browser(url):
    time.sleep(1.0)
    webbrowser.open(url)


def main():
    if yt_dlp is None:
        print("UWAGA: biblioteka yt-dlp nie jest zainstalowana. "
              "Uruchom run_web_windows.bat / run_web_mac_linux.sh albo: pip install -r requirements.txt")

    print("Sprawdzam srodowisko JavaScript (Deno) dla YouTube "
          "(przy pierwszym uruchomieniu pobiera ~40 MB)...")
    if ensure_deno():
        print("OK: Deno gotowe - dostepna pelna jakosc (1080p+).")
    else:
        print("UWAGA: brak Deno - YouTube moze oddawac tylko 360p. "
              "Sprawdz polaczenie z internetem i uruchom ponownie.")

    print("Sprawdzam ffmpeg/ffprobe (przy pierwszym uruchomieniu moze chwile pobierac)...")
    location, has_ffprobe = resolve_ffmpeg()
    if location and has_ffprobe:
        print(f"OK: ffmpeg + ffprobe gotowe ({location}).")
    elif location:
        print("UWAGA: znaleziono ffmpeg, ale brak ffprobe - miniaturki nie beda "
              "osadzane w mp4. Zainstaluj zaleznosci ponownie (static-ffmpeg).")
    else:
        print("UWAGA: brak ffmpeg - laczenie audio+wideo moze nie dzialac.")

    host = "127.0.0.1"
    port = 5000
    url = f"http://{host}:{port}/"

    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    print(f"Serwer wystartował. Jeśli przeglądarka się nie otworzyła automatycznie, wejdź na: {url}")
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        print("Wymagany Python 3.8 lub nowszy.")
        sys.exit(1)
    main()
