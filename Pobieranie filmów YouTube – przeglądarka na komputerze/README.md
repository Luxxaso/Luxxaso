# Pobieracz filmów z YouTube — wersja HTML (w przeglądarce)

Ta wersja działa jak strona internetowa (`index.html`), ale ponieważ sam
YouTube blokuje pobieranie bezpośrednio z poziomu przeglądarki, w tle działa
mały lokalny serwer (Python + yt-dlp), który wykonuje faktyczne pobieranie.
Ty widzisz tylko stronę HTML w przeglądarce.

## Uruchomienie

### Windows

1. Kliknij dwukrotnie **`run_web_windows.bat`**.
2. Przy pierwszym uruchomieniu skrypt zainstaluje potrzebne biblioteki
   (może to potrwać chwilę).
3. Po chwili automatycznie otworzy się przeglądarka ze stroną pobieracza
   (`http://127.0.0.1:5000/`). Jeśli się nie otworzy, wejdź na ten adres ręcznie.
4. Okno terminala (czarne okienko) musi zostać otwarte przez cały czas
   pobierania — to on jest „silnikiem” strony. Możesz je zminimalizować,
   ale nie zamykaj go, dopóki nie skończysz.

### macOS / Linux

1. W terminalu, w tym folderze:
   ```
   chmod +x run_web_mac_linux.sh
   ./run_web_mac_linux.sh
   ```
2. Przeglądarka otworzy się automatycznie pod `http://127.0.0.1:5000/`.

## Jak używać strony

1. Wklej link (lub kilka, po jednym w linii).
2. (Opcjonalnie) kliknij **„Sprawdź linki”** — strona pobierze tytuł, czas
   trwania i miniaturkę, a lista „Jakość” pokaże tylko rozdzielczości, które
   dany film faktycznie oferuje (przy kilku filmach: wspólny pułap).
3. Wybierz jakość i (opcjonalnie) przeglądarkę z ciasteczkami dla filmów
   prywatnych/niepublicznych.
3. Kliknij **„Wybierz...”** przy folderze zapisu, żeby otworzyć prawdziwe
   okno wyboru folderu systemu (zamiast wpisywać ścieżkę ręcznie).
4. Kliknij **Pobierz** — postęp, status każdego linku i log widać na
   bieżąco na stronie. Po zakończeniu strona wyśle powiadomienie
   przeglądarki (jeśli zezwolisz) i zagra krótki dźwięk.

## Dodatkowe opcje

- **Napisy** — zaznacz „Pobierz napisy” i podaj języki (np. `pl,en`).
- **Metadane i miniaturka** — domyślnie włączone; osadza tytuł, autora i
  okładkę bezpośrednio w pobranym pliku.
- **Playlisty** — domyślnie pobierany jest tylko pojedynczy film. Zaznacz
  „Cała playlista”, żeby pobrać wszystkie filmy z playlisty; opcjonalny
  zakres, np. `1-5`.
- **Ponów nieudane** — jeśli któryś link się nie pobierze, przycisk
  pozwoli ponowić tylko te, które zawiodły.
- Strona **zapamiętuje** ostatnio używane ustawienia między uruchomieniami
  serwera.
- Skrypt startowy przy każdym uruchomieniu **aktualizuje yt-dlp** do
  najnowszej wersji.
- **ffmpeg + ffprobe** są pobierane automatycznie (pakiet `static-ffmpeg`)
  przy pierwszym uruchomieniu — potrzebne do łączenia audio/wideo i
  osadzania miniaturki w pliku mp4.
- YouTube wymaga środowiska JavaScript (**Deno**) do rozwiązywania podpisów —
  bez niego dostępny jest tylko format 360p. Aplikacja **pobiera Deno
  automatycznie** przy pierwszym uruchomieniu (~40 MB, do folderu
  `~/.yt_downloader_tools`) i sam silnik EJS z GitHuba. Wymaga to dostępu
  do internetu przy pierwszym pobraniu.

## Vimeo, Facebook i inne serwisy

Link wklejasz tak samo jak z YouTube. Vimeo: od pewnego czasu wiele
publicznych filmów `vimeo.com/<numer>` wymaga zalogowania — ustaw wtedy
**„Ciasteczka z przeglądarki”** na przeglądarkę, w której jesteś zalogowany
na Vimeo. Dla filmów z możliwością osadzania aplikacja sama próbuje adresu
`player.vimeo.com/...`, który zwykle działa bez logowania.

## „This video is not available” / niska jakość / stary film

- **Deno nie zostało pobrane** (brak internetu przy pierwszym uruchomieniu,
  firewall, proxy). Wtedy YouTube oddaje tylko 360p, a część starszych
  filmów zwraca „This video is not available”. Rozwiązanie: uruchom ponownie
  z dostępem do internetu, albo zainstaluj [Deno](https://deno.com/) ręcznie
  i dodaj do PATH. W logu przy starcie widać, czy Deno jest gotowe.
- **Film wymaga logowania / ograniczenie wiekowe lub regionalne** — ustaw
  „Ciasteczka z przeglądarki”.
- **Film usunięty / prywatny** — nie da się nic zrobić.

## Zatrzymanie

Zamknij okno terminala (lub naciśnij Ctrl+C w nim), żeby wyłączyć serwer.

## Uwaga

To rozwiązanie działa **lokalnie na Twoim komputerze** — strona nie jest
wystawiona do internetu, nikt inny się do niej nie dostanie. Pobieraj
wyłącznie treści, do których masz prawo.
