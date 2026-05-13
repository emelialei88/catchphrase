#!/usr/bin/env bash
# Build a one-click Catchphrase binary for the current platform.
# Produces:
#   macOS:   dist/Catchphrase.app
#   Linux:   dist/Catchphrase/Catchphrase
#   Windows: dist/Catchphrase/Catchphrase.exe  (run from a Windows shell)

set -euo pipefail
cd "$(dirname "$0")"

# Use an isolated venv (avoids conda's pathlib backport, etc.)
if [ ! -d ".venv" ]; then
  echo "→ Creating build venv"
  python3 -m venv .venv
fi

echo "→ Installing build dependencies"
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q -r requirements.txt pyinstaller

echo "→ Cleaning previous build"
rm -rf build dist

echo "→ Running PyInstaller"
./.venv/bin/python -m PyInstaller Catchphrase.spec --noconfirm

case "$(uname -s)" in
  Darwin*)
    echo
    echo "✓ Built dist/Catchphrase.app"
    echo "  Double-click it to launch, or drag to /Applications."
    ;;
  Linux*)
    echo
    echo "✓ Built dist/Catchphrase/Catchphrase"
    ;;
  *)
    echo
    echo "✓ Built dist/Catchphrase/"
    ;;
esac
