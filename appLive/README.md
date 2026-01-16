# Fight Detection Monitoring System

Live камера мониторинг с детекцией агрессивных действий и Telegram уведомлениями.

## Возможности

- 🎥 Live детекция с веб-камеры
- 🤖 YOLO11-pose модель с keypoints
- 📱 Telegram уведомления с фото
- 🔄 Умная фильтрация дубликатов
- ⏱ Cooldown между алертами
- 📊 Статистика в реальном времени

## Установка

```bash
cd appLive
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

### Параметры

```bash
python main.py --help

# Примеры:
python main.py --camera 0                    # Камера 0
python main.py --conf 0.6                    # Порог уверенности 60%
python main.py --cooldown 60                 # Cooldown 60 секунд
python main.py --no-telegram                 # Без Telegram уведомлений
python main.py --model /path/to/model.pt    # Другая модель
```

## Настройки

Все настройки в `config.py`:

### Модель
- `MODEL_PATH` - путь к модели
- `CONFIDENCE_THRESHOLD` - порог уверенности (0.5)
- `DETECTION_CLASSES` - классы для детекции [0-7]

### Фильтрация событий
- `EVENT_COOLDOWN` - интервал между алертами (30 сек)
- `EVENT_MIN_DURATION` - мин. длительность события (5 сек)
- `EVENT_MIN_DETECTIONS` - мин. количество детекций (3)
- `EVENT_TIMEOUT` - таймаут без детекции (2 сек)

### Telegram
- `TELEGRAM_ENABLED` - включить уведомления
- `TELEGRAM_BOT_TOKEN` - токен бота
- `TELEGRAM_CHAT_ID` - ID чата/канала

## Классы детекции

| ID | Название | Описание |
|----|----------|----------|
| 0 | bent_over | Наклон вперед |
| 1 | covering_face | Закрытие лица |
| 2 | face_slap | Удар по лицу |
| 3 | fist_clenching | Сжатие кулака |
| 4 | hair_clothes_drag | Таскание за волосы |
| 5 | head_down | Опущенная голова |
| 6 | head_slap_back | Удар по затылку |
| 7 | neck_grab | Захват за шею |
| 8 | neutral_class | Нейтральный (игнорируется) |

## Логика фильтрации

1. **Детекция** → группировка по классам
2. **Начало события** → при первой детекции класса
3. **Накопление** → подсчет детекций, max confidence
4. **Подтверждение** → если:
   - Длительность >= `EVENT_MIN_DURATION`
   - Детекций >= `EVENT_MIN_DETECTIONS`
   - Прошло >= `EVENT_COOLDOWN` с последнего алерта
5. **Уведомление** → Telegram с фото лучшего кадра

## Горячие клавиши

- `q` - выход
- `s` - сохранить скриншот

## Переменные окружения

```bash
export MODEL_PATH=../fight_pose_model_export/best.pt
export CAMERA_INDEX=0
export CONFIDENCE_THRESHOLD=0.5
export EVENT_COOLDOWN=30
export TELEGRAM_ENABLED=True
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id
```

## Структура

```
appLive/
├── main.py           # Основной скрипт
├── config.py         # Конфигурация
├── requirements.txt  # Зависимости
├── events/           # Сохраненные кадры событий (создается автоматически)
└── README.md         # Документация
```
