# Pobieracz filmów z YouTube

Prosta aplikacja z okienkiem (GUI) do pobierania filmów z YouTube (i innych
serwisów obsługiwanych przez [yt-dlp](https://github.com/yt-dlp/yt-dlp)) na
dysk komputera. Nie trzeba używać terminala — wystarczy uruchomić jeden plik.

## Wymagania

- **Python 3.8 lub nowszy** — jeśli nie masz go zainstalowanego, pobierz z
  https://www.python.org/downloads/ (na Windows podczas instalacji zaznacz
  opcję **"Add python.exe to PATH"**).

Wszystkie pozostałe zależności (yt-dlp, ffmpeg) instalują się automatycznie
przy pierwszym uruchomieniu.

## Uruchomienie

### Windows

1. Pobierz/skopiuj cały ten folder na dysk.
2. Kliknij dwukrotnie plik **`run_windows.bat`**.
3. Przy pierwszym uruchomieniu skrypt sam zainstaluje potrzebne biblioteki —
   to może potrwać chwilę. Poczekaj, aż otworzy się okno aplikacji.

### macOS / Linux

1. Otwórz terminal w tym folderze.
2. Nadaj uprawnienie do wykonania (jednorazowo):
   ```
   chmod +x run_mac_linux.sh
   ```
3. Uruchom:
   ```
   ./run_mac_linux.sh
   ```

## Jak używać

1. Wklej link (lub kilka linków, każdy w nowej linii) do pola u góry.
2. Wybierz jakość z listy (np. "Najlepsza jakość", "1080p", albo "Tylko audio (mp3)").
3. Wybierz folder zapisu (domyślnie `Pobrane/Pobrane_filmy`).
4. Kliknij **Pobierz** i poczekaj — postęp widać na pasku i w logu.

## Film prywatny / niepubliczny

Jeśli film nie jest publiczny, a masz do niego dostęp na swoim koncie
Google/YouTube, ustaw pole **"Ciasteczka z przeglądarki"** na przeglądarkę,
w której jesteś zalogowany na tym koncie (np. `chrome`, `firefox`, `edge`).
Aplikacja użyje wtedy Twojej sesji przeglądarki do pobrania filmu — dokładnie
tak, jak flaga `--cookies-from-browser` w yt-dlp.

## Ręczne uruchomienie (opcjonalnie, dla zaawansowanych)

```
pip install -r requirements.txt
python youtube_downloader.py
```

## Uwaga

Pobieraj wyłącznie treści, do których masz prawo (własne nagrania, filmy
udostępnione Tobie, treści na licencji pozwalającej na pobieranie, itp.).
