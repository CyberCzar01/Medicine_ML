#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PYBIN="${PYTHON:-python3}"
"$PYBIN" -m venv .venv
PIP=".venv/bin/pip"

if ! $PIP install -r botkin-urotriage/requirements.txt -r urotriage-webapp/requirements.txt; then
  echo "Повтор с обходом проверки SSL-сертификатов (сети с перехватом трафика)..."
  $PIP install -r botkin-urotriage/requirements.txt -r urotriage-webapp/requirements.txt \
    --trusted-host pypi.org --trusted-host files.pythonhosted.org
fi

echo
echo "Готово. Запуск: ./start.sh"
