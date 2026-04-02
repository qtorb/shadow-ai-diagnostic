#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Uso: $0 <URL_REPO_GITHUB>"
  echo "Ejemplo: $0 git@github.com:tu-org/radar-editorial-social.git"
  exit 1
fi

REPO_URL="$1"
WORKSPACE_DIR="/workspace/Radar editorial social"

if [[ ! -d "$WORKSPACE_DIR" ]]; then
  echo "No existe $WORKSPACE_DIR. Ejecuta primero: ./export_to_workspace.sh"
  exit 1
fi

cd "$WORKSPACE_DIR"

if [[ ! -d .git ]]; then
  git init
fi

git add .

git commit -m "Initial commit: Radar Editorial Social MVP" || true

git branch -M main

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

git push -u origin main

echo "Listo. Proyecto publicado en GitHub: $REPO_URL"
