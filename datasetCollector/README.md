# Dataset Collector & YOLO Annotator

Полный набор инструментов для создания датасета: сбор изображений + разметка bounding boxes для YOLO.

## Скрипты

| Скрипт | Описание |
|--------|----------|
| `collect_dataset_gui.py` | Сбор изображений с камеры |
| `annotate_yolo.py` | Разметка bounding boxes для YOLO |
| `export_yolo_dataset.py` | Экспорт в формат YOLO для обучения |

## Установка

```bash
pip install -r requirements.txt
```

## 1. Сбор данных

```bash
python collect_dataset_gui.py
```

**Особенности:**
- Окно можно изменять (resizable)
- Ручной и автоматический режимы захвата
- Прогресс сохраняется автоматически

### Горячие клавиши (Collector)

| Клавиша | Действие |
|---------|----------|
| `SPACE` | Сделать фото (Manual режим) |
| `A` | Включить Auto режим |
| `M` | Включить Manual режим |
| `N` / `→` | Следующий класс |
| `P` / `←` | Предыдущий класс |
| `Q` | Выход |

## 2. Разметка YOLO

```bash
python annotate_yolo.py
```

**Особенности:**
- Рисование bounding boxes мышкой
- Быстрый выбор классов (клавиши 1-9 или кнопки)
- Сохранение в формате YOLO (нормализованные координаты)
- Навигация между изображениями

### Горячие клавиши (Annotator)

| Клавиша | Действие |
|---------|----------|
| `Мышь` | Рисование bbox (зажать и тянуть) |
| `N` / `→` | Следующее изображение |
| `P` / `←` | Предыдущее изображение |
| `1-9` | Выбор класса |
| `C` | Следующий класс |
| `S` | Сохранить аннотации |
| `D` / `Delete` | Удалить выбранный bbox |
| `Z` | Отменить последний bbox |
| `Q` / `Esc` | Выход |

## 3. Экспорт для обучения

```bash
python export_yolo_dataset.py --val-split 0.2
```

Создает стандартную структуру YOLO:

```
yolo_dataset/
├── images/
│   ├── train/
│   └── val/
├── labels/
│   ├── train/
│   └── val/
├── classes.txt
└── data.yaml
```

### Обучение YOLOv8

```bash
yolo detect train data=yolo_dataset/data.yaml model=yolov8n.pt epochs=100
```

## Структура проекта

```
datasetCollector/
├── collect_dataset_gui.py    # Сбор изображений
├── annotate_yolo.py          # Разметка bbox
├── export_yolo_dataset.py    # Экспорт датасета
├── dataset_classes.json      # Конфигурация классов
├── dataset_progress.json     # Прогресс сбора
├── dataset/                  # Собранные изображения
│   ├── class_name_1/
│   └── class_name_2/
├── annotations/              # Аннотации YOLO
│   ├── class_name_1/
│   └── class_name_2/
├── yolo_dataset/             # Экспортированный датасет
├── requirements.txt
└── README.md
```

## Настройка классов

Редактируйте `dataset_classes.json`:

```json
{
  "classes": [
    {
      "name": "person",
      "target": 100,
      "description": "Человек"
    },
    {
      "name": "car",
      "target": 100,
      "description": "Автомобиль"
    }
  ]
}
```

## Требования

- Python 3.8+
- pygame >= 2.5.0
- opencv-python >= 4.8.0
- numpy >= 1.24.0
- Веб-камера (для сбора данных)
