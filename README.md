# Fight Detection — YOLO11-Pose

Система детекции агрессивных действий на основе YOLO11-pose с веб-интерфейсом и standalone приложением.

## Структура проекта

```
├── fight_pose_model_export/   # Обученная модель YOLO11-pose
│   ├── best.pt               # Модель (не в git, ~40MB)
│   ├── data.yaml             # Конфигурация классов
│   └── live_pose_inference.py
│
├── web/                       # Flask веб-приложение
│   ├── app.py                # Единый файл приложения
│   ├── templates/            # HTML шаблоны (русский язык)
│   └── static/
│
├── appLive/                   # Standalone Pygame приложение
│   ├── main.py               # Главный файл
│   └── config.py             # Конфигурация
│
├── datasetCollector/          # Сборщик датасета
│   ├── collect_dataset_gui.py
│   └── annotate_yolo.py
│
├── yolo_dataset/              # Датасет для обучения
│   ├── images/               # Изображения (не в git)
│   └── labels/               # Аннотации YOLO
│
├── train_yolo.py             # Скрипт обучения
├── prepare_yolo_dataset.py   # Подготовка датасета
└── get_telegram_chat_id.py   # Получение Telegram chat_id
```

## Классы детекции (9 классов)

| ID | Класс | Описание |
|----|-------|----------|
| 0 | bent_over | Наклон вперед |
| 1 | covering_face | Закрытие лица руками |
| 2 | face_slap | Удар ладонью по лицу |
| 3 | fist_clenching | Сжатие кулака |
| 4 | hair_clothes_drag | Таскание за волосы/одежду |
| 5 | head_down | Опущенная голова |
| 6 | head_slap_back | Удар по затылку |
| 7 | neck_grab | Захват за шею |
| 8 | neutral_class | Нейтральный класс |

## Быстрый старт

### 1. Установка

```bash
git clone <repo_url>
cd other_version
pip install -r requirements.txt
```

### 2. Модель

Модель `best.pt` не включена в git (40MB). Варианты:
- Скачать из релизов репозитория
- Обучить заново: `python train_yolo.py`
- Поместить в `fight_pose_model_export/best.pt`

### 3. Запуск веб-приложения

```bash
cd web
pip install -r requirements.txt
python app.py
# Откроется на http://localhost:5001
```

### 4. Запуск standalone приложения

```bash
cd appLive
pip install -r requirements.txt
python main.py
```

## Особенности

- **Веб-интерфейс**: Русский язык, светлая тема, статистика, live-детекция
- **Telegram уведомления**: Отправка при подтвержденных событиях (>5 сек)
- **Event Manager**: Фильтрация дубликатов, cooldown, подтверждение по времени
- **Pose Estimation**: 17 keypoints на человека

## Требования

- Python 3.8+
- OpenCV
- PyTorch
- Ultralytics YOLO
- GPU (рекомендуется, но не обязательно)

## Документация

- `web/README.md` — веб-приложение
- `appLive/README.md` — standalone приложение
- `datasetCollector/README.md` — сборщик датасета
- `fight_pose_model_export/README.md` — описание модели
