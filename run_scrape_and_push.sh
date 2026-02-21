#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# Sunucuda varsa otomatik sanal ortamı aktive et.
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
elif [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
elif [[ -f "../.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "../.venv/bin/activate"
fi

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "Hata: python veya python3 bulunamadi." >&2
  exit 1
fi

"$PYTHON_BIN" main.py

git add -- ihaleler.db

if git diff --cached --quiet -- ihaleler.db; then
  echo "ihaleler.db değişmedi; commit atlanıyor."
  exit 0
fi

if ! git config user.name >/dev/null; then
  git config user.name "kik-bot"
fi

if ! git config user.email >/dev/null; then
  git config user.email "kik-bot@localhost"
fi

git commit -m "Veritabanı güncellendi: $(date '+%Y-%m-%d %H:%M:%S')" -- ihaleler.db
git push origin HEAD
