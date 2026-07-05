# УроТриаж — мобильное веб-приложение (PWA)

Анкета пациента с ОЗМ/ДГПЖ + светофор тяжести для врача-уролога. Работает в браузере на любом телефоне (Android, iPhone), ставится на главный экран как приложение. Журнал принятых решений — `docs/decisions.md`. Инструкция для врача — `ИНСТРУКЦИЯ_ВРАЧУ.md`.

## Если вы клонировали этот репозиторий

Приложению нужен работающий API светофора (репозиторий `botkin-urotriage`). Два варианта:

1. Склонируйте `botkin-urotriage` в соседнюю папку и установите его зависимости — тогда `./run_local.sh` поднимет всё сам (путь можно поменять через `UROTRIAGE_DIR`).
2. Либо укажите адрес уже работающего API: `UROTRIAGE_API_URL=http://адрес:8000 uvicorn app:app --host 0.0.0.0 --port 8080`.

В репозитории нет ни данных пациентов, ни моделей — база `data/records.db` создаётся при первом запуске.

## Как устроено

Два сервера:

1. **API светофора** — существующий `botkin-urotriage` (порт 8000).
2. **Веб-приложение** (`app.py`, порт 8080) — отдаёт мобильный интерфейс, хранит записи в SQLite (`data/records.db`), за зоной ходит в API светофора.

Фронтенд обращается только к относительным путям `/api/...`

## Запуск на localhost

```bash
cd urotriage-webapp
./run_local.sh
```

Скрипт сам находит Python

Отдельная установка (если нужна):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run_local.sh
```

Если pip падает с `SSL: CERTIFICATE_VERIFY_FAILED` (сеть с подменой сертификатов или Python без сертификатов):

```bash
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

Скрипт поднимает оба сервера (светофор из `../botkin-urotriage` и веб-приложение). Открыть: `http://localhost:8080`.

Запуск вручную, если нужно раздельно:

```bash
cd ../botkin-urotriage && uvicorn urotriage.api.main:app --port 8000 &
cd ../urotriage-webapp && UROTRIAGE_API_URL=http://127.0.0.1:8000 uvicorn app:app --host 0.0.0.0 --port 8080
```

Проверить с телефона в той же Wi-Fi-сети: `http://<IP-компьютера>:8080` (IP — в настройках сети).

## Настройки (переменные окружения)

- `UROTRIAGE_API_URL` — адрес API светофора (по умолчанию `http://127.0.0.1:8000`);
- `WEBAPP_DB` — путь к базе SQLite (по умолчанию `data/records.db`);
- порт/хост веб-приложения — аргументы uvicorn.

Если API светофора недоступен, приложение продолжает сохранять записи — зона просто не рассчитывается и досчитается при редактировании записи.

## Endpoints веб-приложения

- `POST /api/records` — сохранить пациента (внутри дергает `/predict` светофора);
- `PUT /api/records/{id}` — дозаполнить/изменить (слияние полей, пересчёт зоны);
- `GET /api/records?q=&zone=&missing_outcome=` — список с поиском и фильтрами;
- `GET /api/records/{id}` — полная запись с разбором светофора;
- `POST /api/triage` — расчёт зоны без сохранения;
- `GET /api/stats` — счётчики для сводки;
- `GET /api/export.xlsx` — все записи в Excel в формате анкеты;
- `GET /api/health` — состояние: база, доступность API светофора.

## Перенос на домен и сервер

1. Скопировать на сервер обе папки: `botkin-urotriage` и `urotriage-webapp`, поставить зависимости обеих.
2. Запустить те же две команды uvicorn (светофор можно оставить на 127.0.0.1 — наружу он не нужен).
3. Поставить nginx перед портом 8080 и выпустить HTTPS-сертификат (например, certbot):

```nginx
server {
    listen 443 ssl;
    server_name urotriage.example.ru;
    ssl_certificate     /etc/letsencrypt/live/urotriage.example.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/urotriage.example.ru/privkey.pem;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
    }
}
```

HTTPS обязателен: без него на телефонах не работает установка PWA и service worker (localhost — единственное исключение). Больше ничего менять не нужно: фронтенд использует относительные пути, CORS не задействован (один origin).

4. Автозапуск — два systemd-юнита (по одному на сервер) или один supervisor-конфиг.

## Данные

- `data/records.db` — все записи врачей. В git не коммитится (`.gitignore`), бэкапить отдельно (это просто один файл — достаточно копировать по расписанию).
- Персональные данные: ФИО не собираются, только № истории болезни.
- Экспорт для обучения модели: кнопка «Скачать Excel» в Сводке или `GET /api/export.xlsx`.

## Тесты

Прогнаны вручную (см. `docs/decisions.md`): сохранение красного/зелёного пациента, валидация № истории, живой светофор, фильтры списка, дозаполнение исхода, экспорт Excel, сохранение при недоступном API светофора.
