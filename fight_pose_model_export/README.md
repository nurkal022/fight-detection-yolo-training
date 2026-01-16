# Fight Detection Pose Model

YOLO11-pose модель для детекции поз при драках.

## Классы (9)

| ID | Название |
|----|----------|
| 0 | bent_over |
| 1 | covering_face |
| 2 | face_slap |
| 3 | fist_clenching |
| 4 | hair_clothes_drag |
| 5 | head_down |
| 6 | head_slap_back |
| 7 | neck_grab |
| 8 | neutral_class |

## Keypoints (17 COCO)

Модель также предсказывает 17 ключевых точек тела:
- 0: nose, 1-2: eyes, 3-4: ears
- 5-6: shoulders, 7-8: elbows, 9-10: wrists
- 11-12: hips, 13-14: knees, 15-16: ankles

## Файлы

- `best.pt` - лучшая модель (использовать для инференса)
- `last.pt` - последняя checkpoint модель
- `data.yaml` - конфигурация датасета
- `args.yaml` - параметры обучения
- `live_pose_inference.py` - скрипт для инференса
- `results.png` - графики обучения
- `confusion_matrix.png` - матрица ошибок

## Использование

### Установка
```bash
pip install ultralytics
```

### Python API
```python
from ultralytics import YOLO

# Загрузка модели
model = YOLO("best.pt")

# Инференс на изображении
results = model.predict("image.jpg", conf=0.5)

# Получение результатов
for r in results:
    boxes = r.boxes      # Bounding boxes
    keypoints = r.keypoints  # Keypoints (17 точек)
    
    for i, box in enumerate(boxes):
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        print(f"Class: {r.names[cls]}, Conf: {conf:.2f}")
```

### CLI
```bash
# Изображение
yolo pose predict model=best.pt source=image.jpg conf=0.5

# Видео
yolo pose predict model=best.pt source=video.mp4 conf=0.5

# Веб-камера
yolo pose predict model=best.pt source=0 conf=0.5 show=True
```

### Скрипт live_pose_inference.py
```bash
# Веб-камера
python live_pose_inference.py --model best.pt --source 0 --conf 0.5

# Видео с сохранением
python live_pose_inference.py --model best.pt --source video.mp4 --save output.mp4 --no-show
```

## Метрики

- **mAP50 (Box)**: ~0.99
- **mAP50 (Pose)**: ~0.99
- **Speed**: ~3.4ms inference per image (GPU)

## Обучение

Модель обучена на YOLO11m-pose с параметрами:
- Эпох: 100
- Размер: 640x640
- Batch: 16

