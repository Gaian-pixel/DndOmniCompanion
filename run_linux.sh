#!/usr/bin/env bash
# ==============================================================================
# D&D OmniCompanion - Quick Launcher for Linux
# ==============================================================================
set -e
cd "$(dirname "$0")"

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "[ERRORE] Python 3 non trovato. Installalo con: sudo apt install python3 python3-tk"
    exit 1
fi

# Check Tkinter
if ! python3 -c "import tkinter" &>/dev/null; then
    echo "[AVVISO] tkinter non trovato nel sistema. Installalo con: sudo apt install python3-tk"
fi

# Launch application
exec python3 main.py "$@"
