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
2. Wybierz jakość i (opcjonalnie) przeglądarkę z ciasteczkami dla filmów
   prywatnych/niepublicznych.
3. Sprawdź/zmień folder zapisu.
4. Kliknij **Pobierz** — postęp i log widać na bieżąco na stronie.

## Zatrzymanie

Zamknij okno terminala (lub naciśnij Ctrl+C w nim), żeby wyłączyć serwer.

## Uwaga

To rozwiązanie działa **lokalnie na Twoim komputerze** — strona nie jest
wystawiona do internetu, nikt inny się do niej nie dostanie. Pobieraj
wyłącznie treści, do których masz prawo.
