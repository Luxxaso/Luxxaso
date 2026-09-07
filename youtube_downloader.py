#!/usr/bin/env python3
"""Prosty pobieracz filmów z YouTube (i innych serwisow obslugiwanych przez yt-dlp).

Graficzny interfejs oparty na Tkinter (wbudowany w Pythona, nie wymaga
dodatkowej instalacji). Do pobierania i łączenia audio/wideo używa
bibliotek yt-dlp oraz imageio-ffmpeg (własny ffmpeg, bez ręcznej
konfiguracji PATH).
"""

import json
import os
import shutil
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None


_ffmpeg_cache = {}


def resolve_ffmpeg():
    """Zwraca (location, has_ffprobe).

    location: katalog z ffmpeg+ffprobe (preferowane) albo sciezka do samego
    ffmpeg. Osadzenie miniaturki w mp4 wymaga ffprobe (lub AtomicParsley).
    """
    if _ffmpeg_cache:
        return _ffmpeg_cache["location"], _ffmpeg_cache["has_ffprobe"]

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


QUALITY_OPTIONS = {
    "Najlepsza jakość (wideo + audio)": "bv*+ba/b",
    "1080p (mp4)": "bv*[height<=1080]+ba/b",
    "720p (mp4)": "bv*[height<=720]+ba/b",
    "480p (mp4)": "bv*[height<=480]+ba/b",
    "Tylko audio (mp3)": "audio",
}

BROWSER_OPTIONS = ["(brak)", "chrome", "firefox", "edge", "brave", "opera", "safari"]

DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "Pobrane_filmy")
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".yt_downloader_config.json")

# RuneScape-inspired palette: dark wood panels with gold trim.
RS_BG = "#1b130a"
RS_PANEL = "#3a2c18"
RS_PANEL_LIGHT = "#55442a"
RS_INPUT_BG = "#241a10"
RS_BORDER = "#6b5636"
RS_GOLD = "#ffd700"
RS_GOLD_DIM = "#c9a227"
RS_TAN = "#e8d5a8"
RS_TAN_DIM = "#9c8964"
RS_GREEN = "#3fd15c"
RS_RED = "#ff5252"

HEADER_FONT_CANDIDATES = ["Press Start 2P", "Perfect DOS VGA 437", "Cascadia Mono", "Consolas", "Menlo", "Courier New"]
BODY_FONT_CANDIDATES = ["VT323", "Perfect DOS VGA 437", "Cascadia Mono", "Consolas", "Menlo", "Courier New"]
LOG_FONT_CANDIDATES = ["Perfect DOS VGA 437", "Consolas", "Menlo", "Courier New"]


def pick_font(root, candidates, size, weight="normal"):
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return (name, size, weight)
    return ("Courier New", size, weight)


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pobieracz filmów z YouTube")
        self.root.geometry("780x700")
        self.root.minsize(700, 620)

        self.is_downloading = False
        self.failed_urls = []
        self.row_by_url_index = {}
        self.config = load_config()
        self._apply_theme()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_theme(self):
        self.font_title = pick_font(self.root, HEADER_FONT_CANDIDATES, 18, "bold")
        self.font_header = pick_font(self.root, HEADER_FONT_CANDIDATES, 11, "bold")
        self.font_body = pick_font(self.root, BODY_FONT_CANDIDATES, 10)
        self.font_log = pick_font(self.root, LOG_FONT_CANDIDATES, 10)

        self.root.configure(bg=RS_BG)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background=RS_BG, foreground=RS_TAN, font=self.font_body)
        style.configure("TFrame", background=RS_BG)
        style.configure("TLabel", background=RS_BG, foreground=RS_TAN, font=self.font_body)
        style.configure("Header.TLabel", background=RS_BG, foreground=RS_GOLD, font=self.font_title, anchor="center")
        style.configure(
            "TLabelframe", background=RS_BG, bordercolor=RS_GOLD_DIM, darkcolor=RS_BG, lightcolor=RS_BG,
            relief="ridge"
        )
        style.configure("TLabelframe.Label", background=RS_BG, foreground=RS_GOLD, font=self.font_header)
        style.configure(
            "TButton", background=RS_PANEL, foreground=RS_GOLD, bordercolor=RS_GOLD_DIM,
            font=self.font_header, padding=6, relief="raised"
        )
        style.map(
            "TButton",
            background=[("active", RS_PANEL_LIGHT), ("disabled", RS_BG)],
            foreground=[("disabled", RS_TAN_DIM)],
        )
        style.configure("TCheckbutton", background=RS_BG, foreground=RS_TAN, font=self.font_body)
        style.map("TCheckbutton", background=[("active", RS_BG)], foreground=[("disabled", RS_TAN_DIM)])
        style.configure(
            "TCombobox", fieldbackground=RS_INPUT_BG, background=RS_PANEL, foreground=RS_TAN,
            arrowcolor=RS_GOLD, bordercolor=RS_BORDER, selectbackground=RS_INPUT_BG,
            selectforeground=RS_TAN, lightcolor=RS_INPUT_BG, darkcolor=RS_INPUT_BG
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", RS_INPUT_BG), ("disabled", RS_BG)],
            foreground=[("readonly", RS_TAN), ("disabled", RS_TAN_DIM)],
            selectbackground=[("readonly", RS_INPUT_BG)],
            selectforeground=[("readonly", RS_TAN)],
            background=[("readonly", RS_PANEL), ("active", RS_PANEL_LIGHT)],
        )
        self.root.option_add("*TCombobox*Listbox.background", RS_INPUT_BG)
        self.root.option_add("*TCombobox*Listbox.foreground", RS_TAN)
        self.root.option_add("*TCombobox*Listbox.selectBackground", RS_PANEL_LIGHT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", RS_GOLD)
        self.root.option_add("*TCombobox*Listbox.font", self.font_body)
        style.configure("TEntry", fieldbackground=RS_INPUT_BG, foreground=RS_TAN, bordercolor=RS_BORDER)
        style.map("TEntry", fieldbackground=[("disabled", RS_BG)])
        style.configure(
            "Horizontal.TProgressbar", troughcolor=RS_INPUT_BG, background=RS_GOLD_DIM,
            bordercolor=RS_BORDER, lightcolor=RS_GOLD, darkcolor=RS_GOLD_DIM
        )
        style.configure(
            "Treeview", background=RS_INPUT_BG, fieldbackground=RS_INPUT_BG, foreground=RS_TAN,
            bordercolor=RS_BORDER, font=self.font_body, rowheight=24
        )
        style.configure("Treeview.Heading", background=RS_PANEL, foreground=RS_GOLD, font=self.font_header)
        style.map("Treeview", background=[("selected", RS_PANEL_LIGHT)], foreground=[("selected", RS_GOLD)])

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}
        cfg = self.config

        header = ttk.Label(self.root, text="*** Pobieracz Filmów ***", style="Header.TLabel")
        header.pack(fill="x", padx=10, pady=(14, 2))

        # URL(s)
        url_frame = ttk.LabelFrame(self.root, text="Link(i) do filmu (jeden na linię, można wkleić kilka)")
        url_frame.pack(fill="x", **pad)
        self.url_text = tk.Text(
            url_frame, height=4, wrap="word", bg=RS_INPUT_BG, fg=RS_TAN, insertbackground=RS_GOLD,
            font=self.font_body, relief="flat", highlightthickness=1, highlightbackground=RS_BORDER,
            highlightcolor=RS_GOLD_DIM
        )
        self.url_text.pack(fill="x", padx=8, pady=8)

        # Options row
        opts_frame = ttk.Frame(self.root)
        opts_frame.pack(fill="x", **pad)

        ttk.Label(opts_frame, text="Jakość:").grid(row=0, column=0, sticky="w")
        self.quality_var = tk.StringVar(value=cfg.get("quality", list(QUALITY_OPTIONS.keys())[0]))
        self.quality_combo = ttk.Combobox(
            opts_frame, textvariable=self.quality_var,
            values=list(QUALITY_OPTIONS.keys()), state="readonly", width=32
        )
        self.quality_combo.grid(row=0, column=1, sticky="w", padx=(6, 20))

        ttk.Label(opts_frame, text="Ciasteczka z przeglądarki:").grid(row=0, column=2, sticky="w")
        self.browser_var = tk.StringVar(value=cfg.get("browser", BROWSER_OPTIONS[0]))
        self.browser_combo = ttk.Combobox(
            opts_frame, textvariable=self.browser_var,
            values=BROWSER_OPTIONS, state="readonly", width=12
        )
        self.browser_combo.grid(row=0, column=3, sticky="w", padx=(6, 0))

        # Extra options
        extra_frame = ttk.LabelFrame(self.root, text="Opcje dodatkowe")
        extra_frame.pack(fill="x", **pad)

        self.subtitles_var = tk.BooleanVar(value=cfg.get("subtitles", False))
        ttk.Checkbutton(
            extra_frame, text="Pobierz napisy, języki:", variable=self.subtitles_var,
            command=self._update_extra_state
        ).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.sub_langs_var = tk.StringVar(value=cfg.get("sub_langs", "pl,en"))
        self.sub_langs_entry = ttk.Entry(extra_frame, textvariable=self.sub_langs_var, width=12)
        self.sub_langs_entry.grid(row=0, column=1, sticky="w", padx=(0, 20))

        self.embed_metadata_var = tk.BooleanVar(value=cfg.get("embed_metadata", True))
        ttk.Checkbutton(
            extra_frame, text="Osadź metadane i miniaturkę", variable=self.embed_metadata_var
        ).grid(row=0, column=2, sticky="w", padx=8)

        self.playlist_var = tk.BooleanVar(value=cfg.get("playlist", False))
        ttk.Checkbutton(
            extra_frame, text="Cała playlista, zakres (opcjonalnie):", variable=self.playlist_var,
            command=self._update_extra_state
        ).grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.playlist_range_var = tk.StringVar(value=cfg.get("playlist_range", ""))
        self.playlist_range_entry = ttk.Entry(extra_frame, textvariable=self.playlist_range_var, width=12)
        self.playlist_range_entry.grid(row=1, column=1, sticky="w")

        # Output folder
        out_frame = ttk.LabelFrame(self.root, text="Folder zapisu")
        out_frame.pack(fill="x", **pad)
        self.output_var = tk.StringVar(value=cfg.get("output_dir", DEFAULT_OUTPUT_DIR))
        out_entry = ttk.Entry(out_frame, textvariable=self.output_var)
        out_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        ttk.Button(out_frame, text="Wybierz...", command=self._choose_folder).pack(side="left", padx=(0, 8), pady=8)

        # Download button + progress
        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", **pad)
        self.download_btn = ttk.Button(action_frame, text="Pobierz", command=self._start_download)
        self.download_btn.pack(side="left")

        self.retry_btn = ttk.Button(action_frame, text="Ponów nieudane", command=self._retry_failed, state="disabled")
        self.retry_btn.pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(action_frame, mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True, padx=10)

        self.status_var = tk.StringVar(value="Gotowy.")
        ttk.Label(self.root, textvariable=self.status_var).pack(fill="x", padx=10)

        # Per-link status list
        list_frame = ttk.LabelFrame(self.root, text="Status pobrań")
        list_frame.pack(fill="both", padx=10, pady=6)
        self.tree = ttk.Treeview(list_frame, columns=("status",), show="tree headings", height=5)
        self.tree.heading("#0", text="Link")
        self.tree.heading("status", text="Status")
        self.tree.column("#0", width=520)
        self.tree.column("status", width=140)
        self.tree.tag_configure("queued", foreground=RS_TAN_DIM)
        self.tree.tag_configure("working", foreground=RS_GOLD)
        self.tree.tag_configure("done", foreground=RS_GREEN)
        self.tree.tag_configure("error", foreground=RS_RED)
        self.tree.pack(fill="x", padx=8, pady=8)

        # Log
        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(
            log_frame, state="disabled", wrap="word", bg="#100b06", fg=RS_TAN_DIM,
            insertbackground=RS_GOLD, font=self.font_log, relief="flat", highlightthickness=1,
            highlightbackground=RS_BORDER, highlightcolor=RS_GOLD_DIM
        )
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        self._update_extra_state()
        self.root.after(60, self._refresh_combo_styles)

        if yt_dlp is None:
            self._log("BŁĄD: biblioteka yt-dlp nie jest zainstalowana. Uruchom instalator "
                       "(run_windows.bat / run_mac_linux.sh) lub wykonaj: pip install -r requirements.txt")

    def _refresh_combo_styles(self):
        # Tk's "clam" theme sometimes fails to paint the readonly Combobox
        # field color on first draw; toggling the state forces a repaint.
        for combo in (self.quality_combo, self.browser_combo):
            combo.state(["!readonly"])
            combo.state(["readonly"])

    def _update_extra_state(self):
        self.sub_langs_entry.configure(state="normal" if self.subtitles_var.get() else "disabled")
        self.playlist_range_entry.configure(state="normal" if self.playlist_var.get() else "disabled")

    def _choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get() or os.path.expanduser("~"))
        if folder:
            self.output_var.set(folder)

    def _log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _current_settings(self):
        return {
            "quality": self.quality_var.get(),
            "browser": self.browser_var.get(),
            "output_dir": self.output_var.get().strip() or DEFAULT_OUTPUT_DIR,
            "subtitles": self.subtitles_var.get(),
            "sub_langs": self.sub_langs_var.get().strip() or "pl,en",
            "embed_metadata": self.embed_metadata_var.get(),
            "playlist": self.playlist_var.get(),
            "playlist_range": self.playlist_range_var.get().strip(),
        }

    def _on_close(self):
        save_config(self._current_settings())
        self.root.destroy()

    def _retry_failed(self):
        if not self.failed_urls:
            return
        self._start_download(urls_override=list(self.failed_urls))

    def _start_download(self, urls_override=None):
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

        if urls_override is not None:
            urls = urls_override
        else:
            urls = [line.strip() for line in self.url_text.get("1.0", "end").splitlines() if line.strip()]
        if not urls:
            messagebox.showwarning("Brak linku", "Wklej przynajmniej jeden link do filmu.")
            return

        settings = self._current_settings()
        output_dir = settings["output_dir"]
        os.makedirs(output_dir, exist_ok=True)
        save_config(settings)

        self.is_downloading = True
        self.failed_urls = []
        self.download_btn.configure(state="disabled")
        self.retry_btn.configure(state="disabled")
        self.progress["value"] = 0
        self.status_var.set("Pobieranie...")

        self.tree.delete(*self.tree.get_children())
        self.row_by_url_index = {}
        for i, url in enumerate(urls):
            iid = f"row{i}"
            display = url if len(url) <= 70 else url[:67] + "..."
            self.tree.insert("", "end", iid=iid, text=display, values=("Oczekuje",), tags=("queued",))
            self.row_by_url_index[i] = iid

        thread = threading.Thread(target=self._download_worker, args=(urls, settings), daemon=True)
        thread.start()

    ROW_STATUS_TAGS = {
        "Oczekuje": "queued",
        "Pobieranie...": "working",
        "Gotowe": "done",
        "Błąd": "error",
    }

    def _set_row_status(self, index, status_text):
        iid = self.row_by_url_index.get(index)
        if iid is not None:
            self.tree.set(iid, "status", status_text)
            self.tree.item(iid, tags=(self.ROW_STATUS_TAGS.get(status_text, "queued"),))

    def _download_worker(self, urls, settings):
        format_selector = QUALITY_OPTIONS[settings["quality"]]
        browser = settings["browser"]

        ffmpeg_location, has_ffprobe = resolve_ffmpeg()

        ydl_opts = {
            "outtmpl": os.path.join(settings["output_dir"], "%(title)s.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "ignoreerrors": True,
            "socket_timeout": 30,
            "retries": 10,
            "fragment_retries": 10,
        }

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

        if settings["subtitles"]:
            langs = [lang.strip() for lang in settings["sub_langs"].split(",") if lang.strip()] or ["pl", "en"]
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = langs
            if not is_audio:
                ydl_opts["embedsubtitles"] = True

        if settings["embed_metadata"]:
            ydl_opts.setdefault("postprocessors", [])
            ydl_opts["postprocessors"] += [{"key": "FFmpegMetadata"}]
            if has_ffprobe or is_audio:
                ydl_opts["writethumbnail"] = True
                ydl_opts["postprocessors"] += [{"key": "EmbedThumbnail"}]
            else:
                self.root.after(0, self._log,
                                "Uwaga: pomijam osadzanie miniaturki (brak ffprobe). "
                                "Zainstaluj zaleznosci ponownie (static-ffmpeg).")

        if settings["playlist"]:
            ydl_opts["noplaylist"] = False
            if settings["playlist_range"]:
                ydl_opts["playlist_items"] = settings["playlist_range"]
        else:
            ydl_opts["noplaylist"] = True

        if ffmpeg_location:
            ydl_opts["ffmpeg_location"] = ffmpeg_location

        if browser and browser != "(brak)":
            ydl_opts["cookiesfrombrowser"] = (browser,)

        had_error = False
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                for i, url in enumerate(urls):
                    self.root.after(0, self._set_row_status, i, "Pobieranie...")
                    self.root.after(0, self._log, f"Rozpoczynam: {url}")
                    try:
                        ydl.download([url])
                        self.root.after(0, self._set_row_status, i, "Gotowe")
                    except Exception as exc:
                        had_error = True
                        self.failed_urls.append(url)
                        self.root.after(0, self._set_row_status, i, "Błąd")
                        self.root.after(0, self._log, f"Błąd przy pobieraniu {url}: {exc}")
        except Exception as exc:
            had_error = True
            self.root.after(0, self._log, f"Nieoczekiwany błąd: {exc}")

        self.root.after(0, self._download_finished, had_error, settings["output_dir"])

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

    def _download_finished(self, had_error, output_dir):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.retry_btn.configure(state="normal" if self.failed_urls else "disabled")
        self.progress["value"] = 100 if not had_error else self.progress["value"]
        self.root.bell()
        if had_error:
            self.status_var.set("Zakończono z błędami — sprawdź log.")
            self._log("Zakończono z błędami. Jeśli film jest prywatny/niepubliczny, "
                       "wybierz przeglądarkę w polu 'Ciasteczka z przeglądarki' (musisz być "
                       "zalogowany w tej przeglądarce na koncie z dostępem do filmu).")
            messagebox.showwarning("Zakończono z błędami", "Część linków się nie pobrała — sprawdź log i spróbuj 'Ponów nieudane'.")
        else:
            self.status_var.set("Gotowe! Pliki zapisane w: " + output_dir)
            self._log("Gotowe.")
            messagebox.showinfo("Gotowe", "Pobieranie zakończone.\nZapisano w: " + output_dir)


def main():
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        print("Wymagany Python 3.8 lub nowszy.")
        sys.exit(1)
    main()
