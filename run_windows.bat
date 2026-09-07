@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Nie znaleziono Pythona. Zainstaluj go z https://www.python.org/downloads/
    echo Podczas instalacji zaznacz opcje "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Tworze srodowisko wirtualne...
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo Instaluje/aktualizuje zaleznosci...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
pip install --upgrade yt-dlp

echo Uruchamiam aplikacje...
python youtube_downloader.py

pause
