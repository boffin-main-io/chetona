#!/usr/bin/env bash
# systemd ছাড়া (Termux/proot, বা যেকোনো plain লিনাক্সে) Chetona-কে
# persistent রাখার সহজ উপায়: crash হলে auto-restart করা একটা loop।
#
# চালানো (background-এ persist করতে):
#   nohup ./run_persistent.sh > /dev/null 2>&1 &
# অথবা tmux/screen সেশনে ফোরগ্রাউন্ডে রেখে ফোন lock করলেও চালু রাখতে
# পারো (Termux-এ termux-wake-lock নেওয়া ভালো, নিচে দেখো)।
set -uo pipefail

SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../server" && pwd)"
cd "$SERVER_DIR"

if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock  # ফোন ঘুমিয়ে গেলে সার্ভার যেন থেমে না যায়
fi

RESTART_DELAY=2
MAX_DELAY=60

echo "Chetona persistent runner শুরু হলো — $SERVER_DIR"
while true; do
  python3 main.py
  EXIT_CODE=$?
  if [ "$EXIT_CODE" -eq 0 ]; then
    echo "সার্ভার পরিষ্কারভাবে বন্ধ হয়েছে (exit 0) — restart loop থামানো হলো।"
    break
  fi
  echo "সার্ভার crash করেছে (exit $EXIT_CODE) — ${RESTART_DELAY}s পর restart করা হবে..."
  sleep "$RESTART_DELAY"
  RESTART_DELAY=$(( RESTART_DELAY * 2 < MAX_DELAY ? RESTART_DELAY * 2 : MAX_DELAY ))
done
