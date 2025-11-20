# Быстрый старт - Standalone приложение

## 1. Установка зависимостей

```bash
cd app2
pip install -r requirements.txt
```

## 2. Запуск приложения

**Приложение полностью автономное - Flask API НЕ нужен!**

```bash
# Базовый запуск (камера 0)
python main.py

# Указать камеру
python main.py --camera 0

# Полноэкранный режим
python main.py --fullscreen

# Список доступных камер
python main.py --list-cameras
```

## Управление

- **ESC** - Выход
- **F** - Переключить полноэкранный режим

## Возможности

✅ Видео поток в реальном времени  
✅ Детекция через YOLO модель  
✅ Статистика (FPS, детекции)  
✅ Уведомления о детекциях  
✅ Звуковые оповещения  
✅ Telegram уведомления (опционально)  
✅ Полноэкранный режим  
✅ **Полностью автономное - без Flask API**

## Конфигурация

Измени `config.py` для настройки:

- `MODEL_PATH` - путь к модели YOLO
- `CAMERA_INDEX` - индекс камеры
- `CONFIDENCE_THRESHOLD` - порог уверенности
- `TELEGRAM_ENABLED` - включить Telegram

## Telegram уведомления (опционально)

Если хочешь получать уведомления в Telegram:

```bash
export TELEGRAM_ENABLED=true
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id
python main.py
```

Или измени в `config.py`.

## Устранение проблем

### "Model file not found"
- Проверь путь к модели в `config.py`
- Или укажи через `--model` параметр

### "Failed to open camera"
- Проверь что камера подключена
- Используй `--list-cameras` чтобы найти доступные камеры
- Попробуй другой индекс камеры

### Низкий FPS
- Уменьши разрешение камеры в `config.py`
- Или уменьши `FPS` в настройках
