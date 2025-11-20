# Standalone Detection Display Application

Полностью автономное нативное приложение для детекции драк без зависимости от Flask API.

## Возможности

- ✅ Прямое подключение к камере через OpenCV
- ✅ Собственная детекция через YOLO модель
- ✅ Отображение видео в реальном времени
- ✅ Overlay статистики (FPS, количество кадров, детекций)
- ✅ Уведомления о новых детекциях
- ✅ Звуковые оповещения
- ✅ Telegram уведомления (опционально)
- ✅ Полноэкранный режим
- ✅ **Полностью автономное - не требует Flask API**

## Установка

```bash
cd app2
pip install -r requirements.txt
```

## Использование

### Базовое использование

```bash
# Запустить с камерой по умолчанию (0)
python main.py

# Указать камеру
python main.py --camera 0

# Указать модель
python main.py --model ../fight_detection/fight_detection_yolo11n2/weights/best.pt

# Полноэкранный режим
python main.py --fullscreen

# Список доступных камер
python main.py --list-cameras
```

### Управление

- **ESC** - Выход
- **F** - Переключить полноэкранный режим

## Конфигурация

Настройки находятся в `config.py`:

- `MODEL_PATH` - Путь к YOLO модели
- `CONFIDENCE_THRESHOLD` - Порог уверенности (0.65)
- `CAMERA_INDEX` - Индекс камеры (0)
- `WINDOW_WIDTH`, `WINDOW_HEIGHT` - Размер окна
- `FPS` - Целевой FPS
- `SHOW_STATS` - Показывать статистику
- `ALERT_SOUND_ENABLED` - Включить звуковые оповещения
- `NOTIFICATIONS_ENABLED` - Показывать уведомления
- `TELEGRAM_ENABLED` - Включить Telegram уведомления
- `TELEGRAM_BOT_TOKEN` - Токен бота
- `TELEGRAM_CHAT_ID` - ID чата

## Переменные окружения

```bash
# Указать модель
export MODEL_PATH=../fight_detection/fight_detection_yolo11n2/weights/best.pt

# Указать камеру
export CAMERA_INDEX=0

# Telegram (опционально)
export TELEGRAM_ENABLED=true
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id
```

## Структура

```
app2/
├── main.py              # Точка входа
├── detector_display.py  # Главное приложение (pygame)
├── detector.py         # YOLO детектор
├── event_manager.py    # Управление событиями
├── notifier.py         # Уведомления (Telegram)
├── config.py           # Конфигурация
├── requirements.txt    # Зависимости
└── README.md          # Документация
```

## Примеры

### Запуск с камерой по умолчанию

```bash
python main.py
```

### Запуск с указанием камеры и модели

```bash
python main.py --camera 0 --model ../fight_detection/fight_detection_yolo11n2/weights/best.pt
```

### Просмотр доступных камер

```bash
python main.py --list-cameras
```

## Требования

- Python 3.8+
- Камера (USB или встроенная)
- YOLO модель (файл .pt)

## Примечания

- Приложение работает полностью автономно
- Не требует Flask API или веб-сервера
- Прямое подключение к камере через OpenCV
- Детекция выполняется локально через YOLO
- Telegram уведомления опциональны
