#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/workspace/Radar editorial social"

mkdir -p "$TARGET_DIR"

rsync -a --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.db' \
  "$SOURCE_DIR/" "$TARGET_DIR/"

echo "Proyecto copiado a: $TARGET_DIR"
echo "Ejecuta: cd \"$TARGET_DIR\" && streamlit run app.py"
