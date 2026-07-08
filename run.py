"""Cross-platform launcher for Survey Studio.

Runs the whole setup with plain Python (no shell line-ending pitfalls):
  1. create a virtual environment (venv/) on first run
  2. install dependencies from requirements.txt
  3. seed demo data (idempotent)
  4. start the server at http://localhost:5000

Usage (any OS):   python run.py
On Windows you can also just double-click run.bat (which calls this file).
"""
import os
import sys
import subprocess
import venv
from pathlib import Path

BASE = Path(__file__).resolve().parent
os.chdir(BASE)

VENV = BASE / "venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], **kw)


def main():
    if not PY.exists():
        print("[1/4] Creating virtual environment (venv)...")
        venv.create(str(VENV), with_pip=True)
    else:
        print("[1/4] Virtual environment found.")

    print("[2/4] Installing dependencies...")
    run([PY, "-m", "pip", "install", "--upgrade", "pip"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = run([PY, "-m", "pip", "install", "-r", "requirements.txt"])
    if r.returncode != 0:
        print("\nERROR: dependency install failed. See messages above.")
        input("Press Enter to exit...")
        return 1

    print("[3/4] Seeding demo data (idempotent)...")
    run([PY, "seed_demo.py"])

    print("[4/4] Starting server...")
    print("=" * 60)
    print("  Open  http://localhost:5000  in your browser")
    print("  Demo login:  demo  /  demo1234")
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    try:
        run([PY, "app.py"])
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
