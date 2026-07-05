#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

API_DIR="${UROTRIAGE_DIR:-../botkin-urotriage}"
API_PORT="${UROTRIAGE_PORT:-8000}"
WEB_PORT="${WEBAPP_PORT:-8080}"

PY=""
for candidate in "../.venv/bin/python" ".venv/bin/python" "$API_DIR/.venv/bin/python"; do
  if [ -x "$candidate" ]; then
    PY="$(cd "$(dirname "$candidate")" && pwd)/python"
    break
  fi
done
if [ -z "$PY" ]; then
  PY="$(command -v python3)"
fi

if ! "$PY" -c "import uvicorn" 2>/dev/null; then
  echo "В окружении $PY нет uvicorn."
  echo "Установите зависимости: $PY -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org"
  exit 1
fi

echo "Python: $PY"

(cd "$API_DIR" && PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" exec "$PY" -m uvicorn urotriage.api.main:app --host 127.0.0.1 --port "$API_PORT") &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT

export UROTRIAGE_API_URL="http://127.0.0.1:$API_PORT"
exec "$PY" -m uvicorn app:app --host 0.0.0.0 --port "$WEB_PORT"
