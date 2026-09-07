# Pobieracz filmów z YouTube

Prosta aplikacja do pobierania filmów z YouTube (i innych serwisów
obsługiwanych przez [yt-dlp](https://github.com/yt-dlp/yt-dlp)) na dysk
komputera. Nie trzeba używać terminala — wystarczy uruchomić jeden plik.

Dostępne są dwie wersje:

- **Ten folder** — aplikacja z natywnym okienkiem (Tkinter).
- **[`web-app/`](web-app/)** — wersja jako strona `index.html` otwierana w
  przeglądarce (w tle działa mały lokalny serwer, który wykonuje pobieranie).

Obie wersje mają te same funkcje — wybierz tę, która bardziej Ci odpowiada.

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
4. Kliknij **Pobierz** i poczekaj — postęp widać na pasku, status każdego
   linku osobno w tabelce, a szczegóły w logu. Po zakończeniu usłyszysz
   dźwięk i zobaczysz okienko z podsumowaniem.

## Dodatkowe opcje

- **Napisy** — zaznacz „Pobierz napisy” i podaj języki (np. `pl,en`).
- **Metadane i miniaturka** — domyślnie włączone; osadza tytuł, autora i
  okładkę (miniaturkę) bezpośrednio w pobranym pliku.
- **Playlisty** — domyślnie pobierany jest tylko pojedynczy film. Zaznacz
  „Cała playlista”, żeby pobrać wszystkie filmy z playlisty; w polu obok
  możesz podać zakres, np. `1-5`.
- **Ponów nieudane** — jeśli któryś link się nie pobierze (np. z powodu
  chwilowego błędu sieci), przycisk pojawi się aktywny i pozwoli ponowić
  tylko te linki, bez powtarzania całości.
- Aplikacja **zapamiętuje** ostatnio używane ustawienia (jakość, folder,
  przeglądarkę itd.) między uruchomieniami.
- Przy każdym uruchomieniu skrypt startowy **aktualizuje yt-dlp** do
  najnowszej wersji — YouTube często się zmienia i stara wersja przestaje
  działać, więc to ważne dla niezawodności.

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
