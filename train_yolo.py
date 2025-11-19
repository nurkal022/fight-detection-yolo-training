#!/usr/bin/env python3
"""
Обучение YOLO модели для детекции объектов
"""

from ultralytics import YOLO
from pathlib import Path
import os

# Конфигурация
MODEL_NAME = 'yolo11n.pt'  # или 'yolo11n-pose.pt' для pose estimation
DATA_YAML = 'yolo_dataset/data.yaml'
EPOCHS = 10
IMG_SIZE = 640
BATCH_SIZE = 16
PROJECT_NAME = 'fight_detection'
MODEL_NAME_OUTPUT = 'fight_detection_yolo11n'

# Максимальное количество ядер
MAX_WORKERS = os.cpu_count() or 8

def train_model():
    """Обучить YOLO модель"""
    
    print("="*60)
    print("ОБУЧЕНИЕ YOLO МОДЕЛИ")
    print("="*60)
    
    # Проверяем наличие датасета
    data_yaml_path = Path(DATA_YAML)
    if not data_yaml_path.exists():
        print(f"❌ Файл конфигурации не найден: {DATA_YAML}")
        print("   Запустите сначала: python prepare_yolo_dataset.py")
        return
    
    print(f"\n📋 Конфигурация:")
    print(f"  Модель: {MODEL_NAME}")
    print(f"  Данные: {DATA_YAML}")
    print(f"  Эпохи: {EPOCHS}")
    print(f"  Размер изображения: {IMG_SIZE}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Workers (ядра): {MAX_WORKERS}")
    
    # Загружаем модель
    print(f"\n📥 Загружаю модель {MODEL_NAME}...")
    try:
        model = YOLO(MODEL_NAME)
        print("✅ Модель загружена")
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        print("   Убедитесь, что ultralytics установлен: pip install ultralytics")
        return
    
    # Обучаем
    print(f"\n🚀 Начинаю обучение...")
    print("   (Это может занять много времени)")
    print()
    
    try:
        results = model.train(
            data=str(data_yaml_path.absolute()),
            epochs=EPOCHS,
            imgsz=IMG_SIZE,
            batch=BATCH_SIZE,
            name=MODEL_NAME_OUTPUT,
            project=PROJECT_NAME,
            patience=20,  # Early stopping если нет улучшения 20 эпох
            save=True,
            plots=True,
            val=True,
            device='cpu',  # Используем CPU (измените на 0 для GPU если доступен)
            workers=MAX_WORKERS,  # Максимальное количество ядер
            optimizer='AdamW',
            lr0=0.001,
            lrf=0.01,
            momentum=0.937,
            weight_decay=0.0005,
            warmup_epochs=3,
            warmup_momentum=0.8,
            warmup_bias_lr=0.1,
            box=7.5,
            cls=0.5,
            dfl=1.5,
            nbs=64,
            hsv_h=0.015,
            hsv_s=0.7,
            hsv_v=0.4,
            degrees=0.0,
            translate=0.1,
            scale=0.5,
            shear=0.0,
            perspective=0.0,
            flipud=0.0,
            fliplr=0.5,
            mosaic=1.0,
            mixup=0.0,
            copy_paste=0.0
        )
        
        print("\n" + "="*60)
        print("✅ ОБУЧЕНИЕ ЗАВЕРШЕНО!")
        print("="*60)
        
        # Путь к лучшей модели
        best_model_path = Path(f'{PROJECT_NAME}/{MODEL_NAME_OUTPUT}/weights/best.pt')
        if best_model_path.exists():
            print(f"\n📦 Лучшая модель сохранена:")
            print(f"   {best_model_path.absolute()}")
            print(f"\n💡 Использование:")
            print(f"   from ultralytics import YOLO")
            print(f"   model = YOLO('{best_model_path}')")
            print(f"   results = model('image.jpg')")
        
        # Последняя модель
        last_model_path = Path(f'{PROJECT_NAME}/{MODEL_NAME_OUTPUT}/weights/last.pt')
        if last_model_path.exists():
            print(f"\n📦 Последняя модель:")
            print(f"   {last_model_path.absolute()}")
        
        print(f"\n📊 Результаты обучения:")
        print(f"   {PROJECT_NAME}/{MODEL_NAME_OUTPUT}/")
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Обучение прервано пользователем")
        print("💾 Модель сохранена в последней точке")
    except Exception as e:
        error_msg = str(e)
        if 'numpy.dtype' in error_msg or 'pandas' in error_msg.lower():
            print(f"\n⚠️  Предупреждение о совместимости numpy/pandas: {error_msg}")
            print("💡 Попробуйте обновить зависимости:")
            print("   pip install --upgrade numpy pandas")
            print("\n💾 Проверяю сохраненные модели...")
            
            # Проверяем, сохранилась ли модель несмотря на ошибку
            best_model_path = Path(f'{PROJECT_NAME}/{MODEL_NAME_OUTPUT}/weights/best.pt')
            last_model_path = Path(f'{PROJECT_NAME}/{MODEL_NAME_OUTPUT}/weights/last.pt')
            
            if best_model_path.exists():
                print(f"✅ Лучшая модель найдена: {best_model_path}")
            elif last_model_path.exists():
                print(f"✅ Последняя модель найдена: {last_model_path}")
            else:
                print("⚠️  Модель не найдена. Попробуйте запустить обучение снова после обновления зависимостей.")
        else:
            print(f"\n❌ Ошибка обучения: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    train_model()

