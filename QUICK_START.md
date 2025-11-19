# Быстрая инструкция по загрузке в Git и запуску на другом компьютере

## 📤 Загрузка в Git (на текущем компьютере)

### 1. Инициализация Git

```bash
cd /Users/nurlykhan/fight_detect/third_try/other_version
git init
```

### 2. Добавление файлов

```bash
git add .
git commit -m "Initial commit: Fight detection YOLO project"
```

### 3. Создание репозитория на GitHub

1. Зайдите на https://github.com
2. Создайте новый репозиторий (например, `fight-detection-yolo`)
3. **НЕ** добавляйте README или .gitignore (они уже есть)

### 4. Подключение и отправка

```bash
# Замените URL на ваш репозиторий
git remote add origin https://github.com/ваш_username/fight-detection-yolo.git
git branch -M main
git push -u origin main
```

**Примечание:** Датасет ~173MB - это нормально для Git, но загрузка может занять время.

---

## 📥 Установка на другом компьютере

### 1. Клонирование

```bash
git clone https://github.com/ваш_username/fight-detection-yolo.git
cd fight-detection-yolo
```

### 2. Установка зависимостей

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
# venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Если есть GPU с CUDA:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 3. Подготовка датасета

```bash
python prepare_yolo_dataset.py
```

### 4. Настройка обучения (если нужно)

Откройте `train_yolo.py` и измените:

```python
EPOCHS = 100              # Количество эпох
BATCH_SIZE = 16          # Уменьшите если не хватает памяти
device = 0               # 0 для GPU, 'cpu' для CPU
MAX_WORKERS = 8          # Количество ядер CPU
```

### 5. Запуск обучения

```bash
python train_yolo.py
```

---

## ⚡ Быстрая проверка

```bash
# Проверить что все файлы на месте
ls -la dataset/
ls -la *.py

# Проверить Python
python --version  # Должно быть 3.8+

# Проверить зависимости
pip list | grep ultralytics
```

---

## 🐛 Решение проблем

### Ошибка "CUDA out of memory"
- Уменьшите `BATCH_SIZE` до 8 или 4
- Уменьшите `IMG_SIZE` до 416

### Медленное обучение
- Используйте GPU: `device = 0` в `train_yolo.py`
- Увеличьте `BATCH_SIZE` если есть память

### Ошибка импорта модулей
```bash
pip install --upgrade -r requirements.txt
```

---

## 📊 Мониторинг обучения

```bash
# Смотреть прогресс
tail -f fight_detection/fight_detection_yolo11n/results.csv

# Проверить использование GPU
nvidia-smi  # Если есть GPU
```

---

## ✅ После обучения

Модель будет в:
```
fight_detection/fight_detection_yolo11n/weights/best.pt
```

Использование:
```python
from ultralytics import YOLO
model = YOLO('fight_detection/fight_detection_yolo11n/weights/best.pt')
results = model('image.jpg')
results[0].show()
```

