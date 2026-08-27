#!/usr/bin/env bash
# systemd থাকা লিনাক্স মেশিনে (যেমন WSL2-এর systemd মোড, বা ডেডিকেটেড
# লিনাক্স বক্স) Chetona-কে boot-এ-persist সার্ভিস হিসেবে ইনস্টল করে।
#
# NOTE: Termux/proot-এ সাধারণত systemd থাকে না — সেক্ষেত্রে
# run_persistent.sh ব্যবহার করো, এটা না।
set -euo pipefail

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../server" && pwd)"
PYTHON_BIN="$(command -v python3)"
SERVICE_FILE="/etc/systemd/system/chetona.service"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl পাওয়া যায়নি — এই মেশিনে systemd নেই।"
  echo "এর বদলে run_persistent.sh ব্যবহার করো।"
  exit 1
fi

echo "Installing dependencies..."
"$PYTHON_BIN" -m pip install -r "$SERVER_DIR/requirements.txt" --quiet

echo "Writing systemd unit to $SERVICE_FILE (needs sudo)..."
sed -e "s|__CHETONA_SERVER_DIR__|$SERVER_DIR|g" \
    -e "s|__CHETONA_PYTHON_BIN__|$PYTHON_BIN|g" \
    "$(dirname "${BASH_SOURCE[0]}")/chetona.service.template" \
    | sudo tee "$SERVICE_FILE" > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable chetona.service
sudo systemctl restart chetona.service

echo "Done. Check status with: sudo systemctl status chetona"
echo "Logs: journalctl -u chetona -f   (or $SERVER_DIR/chetona.log)"
