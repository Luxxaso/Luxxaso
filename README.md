# Pobieracz filmów z YouTube

Proste narzędzie do pobierania filmów z YouTube (oraz innych serwisów
obsługiwanych przez [yt-dlp](https://github.com/yt-dlp/yt-dlp) — m.in.
Vimeo, Facebook, TikTok) na dysk komputera. Nie trzeba używać terminala —
wystarczy uruchomić jeden plik.

## Dwie wersje

| Folder | Opis |
|---|---|
| [**Pobieranie filmów YouTube – przeglądarka na komputerze**](./Pobieranie%20filmów%20YouTube%20–%20przeglądarka%20na%20komputerze/) | Działa jak strona w przeglądarce; w tle chodzi mały lokalny serwer. Ma dodatkowo przycisk „Sprawdź linki” (podgląd filmu + realne rozdzielczości). |
| [**Pobieranie filmów YouTube – aplikacja okienkowa**](./Pobieranie%20filmów%20YouTube%20–%20aplikacja%20okienkowa/) | Natywne okno (Tkinter), bez przeglądarki. |

Obie mają te same podstawowe funkcje (jakość, napisy, metadane, playlisty,
ciasteczka z przeglądarki, ponawianie nieudanych). Wybierz tę, która bardziej
Ci odpowiada — każdy folder ma własny `README.md` z instrukcją.

## Wymagania

- **Python 3.8 lub nowszy** — https://www.python.org/downloads/ (na Windows
  podczas instalacji zaznacz **„Add python.exe to PATH”**).

Pozostałe zależności (yt-dlp, ffmpeg + ffprobe, a także Deno — środowisko
JavaScript potrzebne YouTube do jakości powyżej 360p) pobierają się
automatycznie przy pierwszym uruchomieniu. Potrzebny jest wtedy dostęp
do internetu.

## Szybki start

1. Skopiuj na dysk folder wybranej wersji.
2. Windows: kliknij dwukrotnie `run_windows.bat` (okienkowa) lub
   `run_web_windows.bat` (przeglądarka). macOS/Linux: uruchom odpowiedni
   `*.sh` z terminala.

## Uwaga

Pobieraj wyłącznie treści, do których masz prawo (własne nagrania, materiały
udostępnione Tobie, treści na licencji pozwalającej na pobieranie itp.).
