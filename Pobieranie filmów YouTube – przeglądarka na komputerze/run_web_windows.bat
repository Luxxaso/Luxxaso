@echo off
setlocal

cd /d "%~dp0"

set "PYCMD="
py --version >nul 2>nul
if not errorlevel 1 set "PYCMD=py"

if not defined PYCMD (
    python --version >nul 2>nul
    if not errorlevel 1 set "PYCMD=python"
)

if not defined PYCMD (
    echo Nie znaleziono Pythona. Zainstaluj go z https://www.python.org/downloads/
    echo Podczas instalacji zaznacz opcje "Add python.exe to PATH".
    echo.
    echo Jesli masz Pythona zainstalowanego, a mimo to widzisz ten komunikat,
    echo w Ustawieniach Windows wylacz aliasy "python.exe" i "python3.exe"
    echo w: Aplikacje -^> Zaawansowane ustawienia aplikacji -^> Aliasy wykonywania aplikacji.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Tworze srodowisko wirtualne...
    %PYCMD% -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo Instaluje/aktualizuje zaleznosci...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
pip install --upgrade yt-dlp

echo Uruchamiam serwer i otwieram przegladarke...
python server.py

pause
