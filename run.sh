#!/usr/bin/env bash
# ============================================================
#  Survey Studio - one-click run script for macOS / Linux
#  Run:  chmod +x run.sh && ./run.sh
# ============================================================
set -e
cd "$(dirname "$0")"

# 1) Create a virtual environment on first run
if [ ! -d "venv" ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv venv
fi

# 2) Activate it
source venv/bin/activate

# 3) Install dependencies
echo "[2/4] Installing dependencies..."
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

# 4) Seed demo data (idempotent — only creates what's missing)
echo "[3/4] Seeding demo data..."
python seed_demo.py

echo "[4/4] Starting server..."
echo
echo "============================================================"
echo "  Open  http://localhost:5000  in your browser"
echo "  Demo login:  demo  /  demo1234"
echo "  Press Ctrl+C to stop."
echo "============================================================"
echo
python app.py
