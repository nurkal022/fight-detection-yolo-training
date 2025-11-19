# Руководство по обучению YOLO модели

## Быстрый старт

### 1. Подготовка датасета

```bash
python prepare_yolo_dataset.py
```

Создает структуру:
- `yolo_dataset/images/train/` - обучающие изображения
- `yolo_dataset/images/val/` - валидационные изображения
- `yolo_dataset/labels/train/` - метки для train
- `yolo_dataset/labels/val/` - метки для val
- `yolo_dataset/data.yaml` - конфигурация

### 2. Обучение модели

```bash
python train_yolo.py
```

## Конфигурация

В файле `train_yolo.py` можно настроить:

```python
MODEL_NAME = 'yolo11n.pt'  # Модель для обучения
EPOCHS = 100                # Количество эпох
IMG_SIZE = 640              # Размер изображения
BATCH_SIZE = 16             # Размер батча
device = 'cpu'              # 'cpu' или 0 для GPU
```

## Структура классов

```
0: bent_over
1: covering_face
2: face_slap
3: fist_clenching
4: hair_clothes_drag
5: head_down
6: head_slap_back
7: neck_grab
8: neutral_class
```

## Результаты обучения

После обучения модель будет сохранена в:
- `fight_detection/fight_detection_yolo11n/weights/best.pt` - лучшая модель
- `fight_detection/fight_detection_yolo11n/weights/last.pt` - последняя модель

## Использование обученной модели

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

## Мониторинг обучения

Во время обучения создаются:
- Графики метрик в `fight_detection/fight_detection_yolo11n/`
- Логи обучения
- Визуализация результатов

## Советы

1. **GPU ускорение**: Если есть GPU, измените `device='cpu'` на `device=0` в `train_yolo.py`
2. **Batch size**: Уменьшите batch size если не хватает памяти
3. **Early stopping**: Модель автоматически остановится если нет улучшения 20 эпох
4. **Время обучения**: На CPU обучение может занять несколько часов

