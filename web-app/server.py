#!/usr/bin/env python3
"""Lokalny serwer WWW dla pobieracza filmów z YouTube.

Uruchamia mały serwer Flask na 127.0.0.1, wystawia stronę index.html
(w folderze static/) i proste API, które w tle korzysta z yt-dlp do
pobierania filmów. Przy starcie automatycznie otwiera przeglądarkę.
"""

import json
import os
import subprocess
import sys
import threading
import time
import uuid
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

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


def _run_download(job_id, urls, settings):
    format_selector = QUALITY_FORMATS.get(settings.get("quality", "best"), QUALITY_FORMATS["best"])
    output_dir = settings["output_dir"]

    ydl_opts = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "ignoreerrors": True,
        "progress_hooks": [lambda d: _progress_hook(job_id, d)],
    }

    if format_selector == "audio":
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
        if format_selector != "audio":
            ydl_opts["embedsubtitles"] = True

    if settings.get("embed_metadata"):
        ydl_opts.setdefault("postprocessors", [])
        ydl_opts["writethumbnail"] = True
        ydl_opts["postprocessors"] += [{"key": "FFmpegMetadata"}, {"key": "EmbedThumbnail"}]

    if settings.get("playlist"):
        ydl_opts["noplaylist"] = False
        if settings.get("playlist_range"):
            ydl_opts["playlist_items"] = settings["playlist_range"]
    else:
        ydl_opts["noplaylist"] = True

    if imageio_ffmpeg is not None:
        try:
            ydl_opts["ffmpeg_location"] = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass

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
                    had_error = True
                    _set_item_status(job_id, i, "error")
                    _job_log(job_id, f"Błąd przy pobieraniu {url}: {exc}")
    except Exception as exc:
        had_error = True
        _job_log(job_id, f"Nieoczekiwany błąd: {exc}")

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
