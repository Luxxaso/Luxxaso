# Pobieranie filmów YouTube – aplikacja okienkowa

Aplikacja z natywnym okienkiem (Tkinter) do pobierania filmów z YouTube
(i innych serwisów obsługiwanych przez [yt-dlp](https://github.com/yt-dlp/yt-dlp)
— m.in. Vimeo) na dysk komputera. Nie trzeba używać terminala — wystarczy
uruchomić jeden plik.

> Wolisz obsługę w przeglądarce, z podglądem filmu przed pobraniem? Zobacz
> folder **„Pobieranie filmów YouTube – przeglądarka na komputerze”**.

## Wymagania

- **Python 3.8 lub nowszy** — jeśli nie masz go zainstalowanego, pobierz z
  https://www.python.org/downloads/ (na Windows podczas instalacji zaznacz
  opcję **"Add python.exe to PATH"**).

Wszystkie pozostałe zależności (yt-dlp, ffmpeg + ffprobe) instalują się
automatycznie przy pierwszym uruchomieniu.

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
- **ffmpeg + ffprobe** pobierane są automatycznie (pakiet `static-ffmpeg`)
  przy pierwszym uruchomieniu — potrzebne do łączenia audio/wideo i
  osadzania miniaturki w pliku mp4.

## Film prywatny / niepubliczny

Jeśli film nie jest publiczny, a masz do niego dostęp na swoim koncie
Google/YouTube, ustaw pole **"Ciasteczka z przeglądarki"** na przeglądarkę,
w której jesteś zalogowany na tym koncie (np. `chrome`, `firefox`, `edge`).
Aplikacja użyje wtedy Twojej sesji przeglądarki do pobrania filmu — dokładnie
tak, jak flaga `--cookies-from-browser` w yt-dlp.

## Vimeo, Facebook i inne serwisy

Wklejasz link tak samo jak z YouTube. Uwaga na Vimeo: od pewnego czasu wiele
publicznych filmów `vimeo.com/<numer>` yt-dlp potrafi pobrać dopiero po
zalogowaniu — ustaw wtedy **„Ciasteczka z przeglądarki”** na przeglądarkę,
w której jesteś zalogowany na Vimeo. Filmy z możliwością osadzania
(`player.vimeo.com/...`) zwykle działają bez logowania.

## „This video is not available” / stary film

Najczęstsze przyczyny i co robić:

- **Brak środowiska JavaScript (Deno).** Nowe wersje yt-dlp do pełnej obsługi
  YouTube potrzebują runtime JS. Bez niego część starszych filmów zwraca
  „This video is not available” albo „The page needs to be reloaded”.
  Aplikacja próbuje wtedy alternatywnych klientów (android/ios/tv), co
  ratuje większość przypadków — ale w niższej rozdzielczości. Pełne
  rozwiązanie: zainstaluj [Deno](https://deno.com/) i dodaj do PATH.
- **Film wymaga logowania / jest ograniczony wiekowo lub regionalnie** —
  ustaw „Ciasteczka z przeglądarki”.
- **Film został usunięty / jest prywatny** — wtedy nie da się nic zrobić.

## Ręczne uruchomienie (opcjonalnie, dla zaawansowanych)

```
pip install -r requirements.txt
python youtube_downloader.py
```

## Uwaga

Pobieraj wyłącznie treści, do których masz prawo (własne nagrania, filmy
udostępnione Tobie, treści na licencji pozwalającej na pobieranie, itp.).
