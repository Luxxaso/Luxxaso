#!/usr/bin/env python3
"""Prosty pobieracz filmów z YouTube (i innych serwisow obslugiwanych przez yt-dlp).

Graficzny interfejs oparty na Tkinter (wbudowany w Pythona, nie wymaga
dodatkowej instalacji). Do pobierania i łączenia audio/wideo używa
bibliotek yt-dlp oraz imageio-ffmpeg (własny ffmpeg, bez ręcznej
konfiguracji PATH).
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


QUALITY_OPTIONS = {
    "Najlepsza jakość (wideo + audio)": "bv*+ba/b",
    "1080p (mp4)": "bv*[height<=1080]+ba/b",
    "720p (mp4)": "bv*[height<=720]+ba/b",
    "480p (mp4)": "bv*[height<=480]+ba/b",
    "Tylko audio (mp3)": "audio",
}

BROWSER_OPTIONS = ["(brak)", "chrome", "firefox", "edge", "brave", "opera", "safari"]

DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "Pobrane_filmy")


class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pobieracz filmów z YouTube")
        self.root.geometry("720x560")
        self.root.minsize(640, 480)

        self.is_downloading = False
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # URL(s)
        url_frame = ttk.LabelFrame(self.root, text="Link(i) do filmu (jeden na linię, można wkleić kilka)")
        url_frame.pack(fill="x", **pad)
        self.url_text = tk.Text(url_frame, height=4, wrap="word")
        self.url_text.pack(fill="x", padx=8, pady=8)

        # Options row
        opts_frame = ttk.Frame(self.root)
        opts_frame.pack(fill="x", **pad)

        ttk.Label(opts_frame, text="Jakość:").grid(row=0, column=0, sticky="w")
        self.quality_var = tk.StringVar(value=list(QUALITY_OPTIONS.keys())[0])
        quality_combo = ttk.Combobox(
            opts_frame, textvariable=self.quality_var,
            values=list(QUALITY_OPTIONS.keys()), state="readonly", width=32
        )
        quality_combo.grid(row=0, column=1, sticky="w", padx=(6, 20))

        ttk.Label(opts_frame, text="Ciasteczka z przeglądarki:").grid(row=0, column=2, sticky="w")
        self.browser_var = tk.StringVar(value=BROWSER_OPTIONS[0])
        browser_combo = ttk.Combobox(
            opts_frame, textvariable=self.browser_var,
            values=BROWSER_OPTIONS, state="readonly", width=12
        )
        browser_combo.grid(row=0, column=3, sticky="w", padx=(6, 0))

        # Output folder
        out_frame = ttk.LabelFrame(self.root, text="Folder zapisu")
        out_frame.pack(fill="x", **pad)
        self.output_var = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        out_entry = ttk.Entry(out_frame, textvariable=self.output_var)
        out_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        ttk.Button(out_frame, text="Wybierz...", command=self._choose_folder).pack(side="left", padx=(0, 8), pady=8)

        # Download button + progress
        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", **pad)
        self.download_btn = ttk.Button(action_frame, text="Pobierz", command=self._start_download)
        self.download_btn.pack(side="left")

        self.progress = ttk.Progressbar(action_frame, mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True, padx=10)

        self.status_var = tk.StringVar(value="Gotowy.")
        ttk.Label(self.root, textvariable=self.status_var).pack(fill="x", padx=10)

        # Log
        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        if yt_dlp is None:
            self._log("BŁĄD: biblioteka yt-dlp nie jest zainstalowana. Uruchom instalator "
                       "(run_windows.bat / run_mac_linux.sh) lub wykonaj: pip install -r requirements.txt")

    def _choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get() or os.path.expanduser("~"))
        if folder:
            self.output_var.set(folder)

    def _log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _start_download(self):
        if self.is_downloading:
            return

        if yt_dlp is None:
            messagebox.showerror(
                "Brak zależności",
                "Biblioteka yt-dlp nie jest zainstalowana.\n\n"
                "Uruchom run_windows.bat (Windows) lub run_mac_linux.sh (Mac/Linux), "
                "albo w terminalu wpisz: pip install -r requirements.txt"
            )
            return

        urls = [line.strip() for line in self.url_text.get("1.0", "end").splitlines() if line.strip()]
        if not urls:
            messagebox.showwarning("Brak linku", "Wklej przynajmniej jeden link do filmu.")
            return

        output_dir = self.output_var.get().strip() or DEFAULT_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.is_downloading = True
        self.download_btn.configure(state="disabled")
        self.progress["value"] = 0
        self.status_var.set("Pobieranie...")

        thread = threading.Thread(target=self._download_worker, args=(urls, output_dir), daemon=True)
        thread.start()

    def _download_worker(self, urls, output_dir):
        quality_key = self.quality_var.get()
        format_selector = QUALITY_OPTIONS[quality_key]
        browser = self.browser_var.get()

        ydl_opts = {
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "noplaylist": False,
            "ignoreerrors": True,
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

        if browser and browser != "(brak)":
            ydl_opts["cookiesfrombrowser"] = (browser,)

        had_error = False
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for url in urls:
                    self.root.after(0, self._log, f"Rozpoczynam: {url}")
                    try:
                        ydl.download([url])
                    except Exception as exc:
                        had_error = True
                        self.root.after(0, self._log, f"Błąd przy pobieraniu {url}: {exc}")
        except Exception as exc:
            had_error = True
            self.root.after(0, self._log, f"Nieoczekiwany błąd: {exc}")

        self.root.after(0, self._download_finished, had_error)

    def _progress_hook(self, d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                percent = downloaded / total * 100
                self.root.after(0, self._update_progress, percent, d.get("filename", ""))
        elif d.get("status") == "finished":
            self.root.after(0, self._log, f"Pobrano, przetwarzanie: {os.path.basename(d.get('filename', ''))}")

    def _update_progress(self, percent, filename):
        self.progress["value"] = percent
        self.status_var.set(f"Pobieranie... {percent:.1f}%  {os.path.basename(filename)}")

    def _download_finished(self, had_error):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.progress["value"] = 100 if not had_error else self.progress["value"]
        if had_error:
            self.status_var.set("Zakończono z błędami — sprawdź log.")
            self._log("Zakończono z błędami. Jeśli film jest prywatny/niepubliczny, "
                       "wybierz przeglądarkę w polu 'Ciasteczka z przeglądarki' (musisz być "
                       "zalogowany w tej przeglądarce na koncie z dostępem do filmu).")
        else:
            self.status_var.set("Gotowe! Pliki zapisane w: " + self.output_var.get())
            self._log("Gotowe.")


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    app = DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        print("Wymagany Python 3.8 lub nowszy.")
        sys.exit(1)
    main()
