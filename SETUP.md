# Инструкция по установке и запуску проекта

## Требования

- Python 3.8+
- Git
- Минимум 8GB RAM (рекомендуется 16GB+)
- GPU (опционально, но рекомендуется для обучения)

## Шаг 1: Клонирование репозитория

```bash
git clone <ваш_repo_url>
cd other_version
```

## Шаг 2: Установка зависимостей

```bash
# Создать виртуальное окружение (рекомендуется)
python -m venv venv

# Активировать виртуальное окружение
# Linux/Mac:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Если есть GPU (CUDA), установите PyTorch с поддержкой CUDA:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## Шаг 3: Проверка структуры датасета

Убедитесь, что датасет находится в папке `dataset/` со следующей структурой:

```
dataset/
├── bent_over/
│   ├── *.jpg
│   └── *.txt
├── covering_face/
│   ├── *.jpg
│   └── *.txt
├── face_slap/
│   ├── *.jpg
│   └── *.txt
├── fist_clenching/
│   ├── *.jpg
│   └── *.txt
├── hair_clothes_drag/
│   ├── *.jpg
│   └── *.txt
├── head_down/
│   ├── *.jpg
│   └── *.txt
├── head_slap_back/
│   ├── *.jpg
│   └── *.txt
├── neck_grab/
│   ├── *.jpg
│   └── *.txt
└── neutral_class/
    ├── *.jpg
    └── *.txt
```

## Шаг 4: Подготовка датасета для YOLO

```bash
python prepare_yolo_dataset.py
```

Это создаст структуру `yolo_dataset/` с разделением на train/val и файл `data.yaml`.

## Шаг 5: Настройка обучения (опционально)

Откройте `train_yolo.py` и настройте параметры:

```python
EPOCHS = 100              # Количество эпох
IMG_SIZE = 640            # Размер изображения
BATCH_SIZE = 16           # Размер батча (уменьшите если не хватает памяти)
device = 'cpu'            # 'cpu' или 0 для GPU
MAX_WORKERS = 8           # Количество ядер CPU
```

## Шаг 6: Запуск обучения

```bash
python train_yolo.py
```

### Для GPU (если доступен):

В файле `train_yolo.py` измените:
```python
device = 0  # или 'cuda:0'
```

## Шаг 7: Использование обученной модели

После обучения модель будет сохранена в:
```
fight_detection/fight_detection_yolo11n/weights/best.pt
```

Пример использования:

```python
from ultralytics import YOLO

# Загрузить модель
model = YOLO('fight_detection/fight_detection_yolo11n/weights/best.pt')

# Детекция на изображении
results = model('image.jpg')
results[0].show()

# Детекция на видео
results = model('video.mp4', save=True)
```

## Структура классов

Модель обучена на 9 классах:

```
0: bent_over          - Наклон вперед
1: covering_face      - Закрытие лица руками
2: face_slap          - Удар ладонью по лицу
3: fist_clenching     - Сжатие кулака
4: hair_clothes_drag  - Таскание за волосы/одежду
5: head_down          - Опущенная голова
6: head_slap_back     - Удар по затылку
7: neck_grab          - Захват за шею
8: neutral_class      - Нейтральный класс
```

## Устранение проблем

### Ошибка "CUDA out of memory"
- Уменьшите `BATCH_SIZE` в `train_yolo.py`
- Уменьшите `IMG_SIZE` (например, до 416)

### Ошибка "numpy.dtype size changed"
```bash
pip install --upgrade numpy pandas
```

### Медленное обучение на CPU
- Используйте GPU если доступен
- Уменьшите количество эпох для тестирования
- Уменьшите размер изображения

## Дополнительные скрипты

- `fix_dataset_structure.py` - исправление структуры датасета
- `fix_label_classes.py` - исправление классов в метках
- `sync_labels.py` - синхронизация меток с изображениями
- `collect_dataset_gui.py` - GUI для сбора датасета

## Мониторинг обучения

Во время обучения можно отслеживать прогресс:

```bash
# Просмотр результатов
tail -f fight_detection/fight_detection_yolo11n/results.csv

# Просмотр графиков (после обучения)
ls fight_detection/fight_detection_yolo11n/
```

## Контакты и поддержка

При возникновении проблем проверьте:
1. Версии Python и зависимостей
2. Доступность GPU (если используется)
3. Размер датасета и меток

