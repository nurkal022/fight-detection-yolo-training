# Fight Detection Web Application

Flask веб-приложение для мониторинга детекции агрессивных действий.

## Возможности

- Live видео с детекцией в реальном времени
- Автоматические Telegram уведомления
- Подробное логирование в БД и файл
- WebSocket обновления в реальном времени
- История событий с сохраненными кадрами

## Установка

```bash
cd web
pip install -r requirements.txt
```

## Запуск

```bash
python app.py
```

Откроется на `http://localhost:5001`

## Страницы

- `/` - Dashboard со статистикой и управлением
- `/live` - Live видео поток
- `/events` - История событий
- `/logs` - Системные логи

## API

- `GET /api/status` - Статус детектора
- `POST /api/start` - Запустить детекцию
- `POST /api/stop` - Остановить детекцию
- `GET /api/events` - Список событий
- `GET /api/logs` - Системные логи
- `GET /api/stats` - Статистика
- `GET /video_feed` - MJPEG видео поток

## Настройки

Переменные окружения:

```bash
export MODEL_PATH=../fight_pose_model_export/best.pt
export CONFIDENCE_THRESHOLD=0.5
export EVENT_COOLDOWN=30
export EVENT_MIN_DURATION=5.0
export TELEGRAM_ENABLED=True
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id
```

## Структура

```
web/
├── app.py              # Основное приложение
├── templates/          # HTML шаблоны
│   ├── base.html
│   ├── index.html
│   ├── live.html
│   ├── events.html
│   └── logs.html
├── static/
│   └── events/         # Сохраненные кадры событий
├── logs/               # Логи приложения
├── app.db              # SQLite база данных
└── requirements.txt
```

## Фильтрация событий

Уведомление отправляется только если:
1. Детекция длится >= 5 секунд
2. >= 3 детекций за время события
3. Прошло >= 30 секунд с последнего алерта этого класса
