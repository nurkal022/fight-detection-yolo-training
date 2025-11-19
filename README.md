# Fight Detection YOLO Training Project

Проект для обучения YOLO модели детекции агрессивных действий и конфликтов.

## Быстрый старт

### 1. Клонирование и установка

```bash
git clone <repo_url>
cd other_version
pip install -r requirements.txt
```

### 2. Подготовка датасета

```bash
python prepare_yolo_dataset.py
```

### 3. Обучение модели

```bash
python train_yolo.py
```

## Структура проекта

```
other_version/
├── dataset/                    # Исходный датасет с изображениями и метками
├── yolo_dataset/               # Подготовленный датасет для YOLO (создается автоматически)
├── app/                        # Flask веб-приложение
├── collect_dataset_gui.py      # GUI для сбора датасета
├── prepare_yolo_dataset.py     # Подготовка датасета для YOLO
├── train_yolo.py              # Скрипт обучения модели
├── fix_dataset_structure.py   # Исправление структуры датасета
└── requirements.txt           # Зависимости Python
```

## Классы детекции

- `bent_over` - Наклон вперед
- `covering_face` - Закрытие лица руками
- `face_slap` - Удар ладонью по лицу
- `fist_clenching` - Сжатие кулака
- `hair_clothes_drag` - Таскание за волосы/одежду
- `head_down` - Опущенная голова
- `head_slap_back` - Удар по затылку
- `neck_grab` - Захват за шею
- `neutral_class` - Нейтральный класс

## Документация

- `SETUP.md` - Подробная инструкция по установке
- `GIT_SETUP.md` - Инструкция по загрузке в Git
- `TRAINING_GUIDE.md` - Руководство по обучению

## Требования

- Python 3.8+
- 8GB+ RAM
- GPU (опционально, но рекомендуется)

## Лицензия

[Укажите вашу лицензию]
