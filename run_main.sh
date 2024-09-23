#!/bin/bash

# Nastavte pracovní adresář na adresář, kde se nachází skript
cd "$(dirname "$0")"

# Aktivujte virtuální prostředí (pokud je použito)
# source venv/bin/activate

# Spusťte Python skript
sudo python3 main.py

