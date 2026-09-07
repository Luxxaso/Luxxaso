#!/usr/bin/env python3
"""Lokalny serwer WWW dla pobieracza filmów z YouTube.

Uruchamia mały serwer Flask na 127.0.0.1, wystawia stronę index.html
(w folderze static/) i proste API, które w tle korzysta z yt-dlp do
pobierania filmów. Przy starcie automatycznie otwiera przeglądarkę.
"""

import os
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

QUALITY_FORMATS = {
    "best": "bv*+ba/b",
    "1080p": "bv*[height<=1080]+ba/b",
    "720p": "bv*[height<=720]+ba/b",
    "480p": "bv*[height<=480]+ba/b",
    "audio": "audio",
}

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

jobs = {}
jobs_lock = threading.Lock()


def _job_log(job_id, message):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is not None:
            job["log"].append(message)


def _run_download(job_id, urls, quality, browser, output_dir):
    format_selector = QUALITY_FORMATS.get(quality, QUALITY_FORMATS["best"])

    ydl_opts = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "noplaylist": False,
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

    if imageio_ffmpeg is not None:
        try:
            ydl_opts["ffmpeg_location"] = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass

    if browser and browser != "none":
        ydl_opts["cookiesfrombrowser"] = (browser,)

    had_error = False
    try:
        os.makedirs(output_dir, exist_ok=True)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in urls:
                _job_log(job_id, f"Rozpoczynam: {url}")
                try:
                    ydl.download([url])
                except Exception as exc:
                    had_error = True
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


@app.route("/api/default-output-dir")
def default_output_dir():
    return jsonify({"path": DEFAULT_OUTPUT_DIR})


@app.route("/api/download", methods=["POST"])
def start_download():
    if yt_dlp is None:
        return jsonify({"error": "Biblioteka yt-dlp nie jest zainstalowana."}), 500

    data = request.get_json(force=True) or {}
    urls = [u.strip() for u in data.get("urls", []) if u.strip()]
    if not urls:
        return jsonify({"error": "Podaj przynajmniej jeden link."}), 400

    quality = data.get("quality", "best")
    browser = data.get("browser", "none")
    output_dir = data.get("output_dir") or DEFAULT_OUTPUT_DIR

    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {
            "status": "downloading",
            "percent": 0,
            "current_file": "",
            "log": [],
            "created": time.time(),
        }

    thread = threading.Thread(
        target=_run_download, args=(job_id, urls, quality, browser, output_dir), daemon=True
    )
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
