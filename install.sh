#!/bin/bash

# Nastavení proměnných
REPO_URL="https://github.com/m-klecka/123smartbms-display/archive/refs/heads/main.zip"
INSTALL_DIR="/home/michael/smartbms-display"
SERVICE_NAME="smartbms.service"

# Stažení a rozbalení projektu
echo "Stahuji projekt..."
wget -O main.zip $REPO_URL
unzip main.zip -d $INSTALL_DIR
cd $INSTALL_DIR

# Vytvoření Python environmentu a instalace potřebných balíčků
echo "Vytvářím Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt flask serial_asyncio

# Nastavení systemd služby
echo "Vytvářím systemd službu..."
echo "[Unit]
Description=SmartBMS Webserver
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/smartbms.py
Restart=always

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/$SERVICE_NAME

# Načtení nové služby a její povolení
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

# Ukončení
echo "Instalace dokončena. SmartBMS server běží jako služba pod názvem '$SERVICE_NAME'."
