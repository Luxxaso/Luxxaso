#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
    echo "Nie znaleziono Pythona 3. Zainstaluj go (np. z https://www.python.org/downloads/ lub przez menedzera pakietow systemu)."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Tworze srodowisko wirtualne..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Instaluje/aktualizuje zaleznosci..."
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo "Uruchamiam serwer i otwieram przegladarke..."
python server.py
