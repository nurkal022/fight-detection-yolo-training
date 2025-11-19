#!/usr/bin/env python3
"""
Подготовка датасета для обучения YOLO
Создает структуру train/val и data.yaml
"""

import os
import shutil
import random
from pathlib import Path
import json

DATASET_DIR = Path('dataset')
YOLO_DATASET_DIR = Path('yolo_dataset')

# Маппинг классов
CLASS_MAPPING = {
    0: 'bent_over',
    1: 'covering_face',
    2: 'face_slap',
    3: 'fist_clenching',
    4: 'hair_clothes_drag',
    5: 'head_down',
    6: 'head_slap_back',
    7: 'neck_grab',
    8: 'neutral_class'
}

def prepare_yolo_dataset():
    """Подготовить датасет в формате YOLO"""
    
    print("="*60)
    print("ПОДГОТОВКА ДАТАСЕТА ДЛЯ YOLO")
    print("="*60)
    
    # Создаем структуру
    (YOLO_DATASET_DIR / 'images' / 'train').mkdir(parents=True, exist_ok=True)
    (YOLO_DATASET_DIR / 'images' / 'val').mkdir(parents=True, exist_ok=True)
    (YOLO_DATASET_DIR / 'labels' / 'train').mkdir(parents=True, exist_ok=True)
    (YOLO_DATASET_DIR / 'labels' / 'val').mkdir(parents=True, exist_ok=True)
    
    # Собираем все изображения с метками
    all_files = []
    
    print("\n📋 Сканирую датасет...")
    for class_idx, class_name in CLASS_MAPPING.items():
        class_dir = DATASET_DIR / class_name
        
        if not class_dir.exists():
            print(f"⚠️  Папка {class_name} не найдена")
            continue
        
        for img_file in class_dir.glob('*.jpg'):
            label_file = class_dir / f"{img_file.stem}.txt"
            
            if not label_file.exists():
                # Пробуем другие расширения изображений
                for ext in ['.jpeg', '.png']:
                    alt_img = class_dir / f"{img_file.stem}{ext}"
                    if alt_img.exists():
                        img_file = alt_img
                        break
                
                label_file = class_dir / f"{img_file.stem}.txt"
                if not label_file.exists():
                    continue
            
            all_files.append((img_file, label_file, class_idx))
    
    print(f"✅ Найдено файлов: {len(all_files)}")
    
    if len(all_files) == 0:
        print("❌ Не найдено файлов для обучения!")
        return False
    
    # Разделяем на train/val (80/20)
    print("\n📊 Разделяю на train/val (80/20)...")
    random.seed(42)
    random.shuffle(all_files)
    
    split_idx = int(len(all_files) * 0.8)
    train_data = all_files[:split_idx]
    val_data = all_files[split_idx:]
    
    print(f"  Train: {len(train_data)} файлов")
    print(f"  Val: {len(val_data)} файлов")
    
    # Копируем train
    print("\n📁 Копирую train данные...")
    for idx, (img_file, label_file, class_idx) in enumerate(train_data):
        # Копируем изображение
        shutil.copy2(img_file, YOLO_DATASET_DIR / 'images' / 'train' / img_file.name)
        
        # Копируем метку (класс уже правильный в метке)
        shutil.copy2(label_file, YOLO_DATASET_DIR / 'labels' / 'train' / label_file.name)
        
        if (idx + 1) % 50 == 0:
            print(f"  Скопировано: {idx + 1}/{len(train_data)}")
    
    # Копируем val
    print("\n📁 Копирую val данные...")
    for idx, (img_file, label_file, class_idx) in enumerate(val_data):
        shutil.copy2(img_file, YOLO_DATASET_DIR / 'images' / 'val' / img_file.name)
        shutil.copy2(label_file, YOLO_DATASET_DIR / 'labels' / 'val' / label_file.name)
        
        if (idx + 1) % 50 == 0:
            print(f"  Скопировано: {idx + 1}/{len(val_data)}")
    
    # Создаем data.yaml
    print("\n📝 Создаю data.yaml...")
    data_yaml = f"""# YOLO Dataset Configuration
# Путь к датасету (абсолютный или относительный)
path: {YOLO_DATASET_DIR.absolute()}

# Пути к train и val (относительно path)
train: images/train
val: images/val

# Количество классов
nc: {len(CLASS_MAPPING)}

# Имена классов
names:
"""
    for class_idx, class_name in CLASS_MAPPING.items():
        data_yaml += f"  {class_idx}: {class_name}\n"
    
    yaml_path = YOLO_DATASET_DIR / 'data.yaml'
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(data_yaml)
    
    print(f"✅ data.yaml создан: {yaml_path}")
    
    # Статистика по классам
    print("\n📊 Статистика по классам:")
    class_counts = {}
    for _, _, class_idx in all_files:
        class_counts[class_idx] = class_counts.get(class_idx, 0) + 1
    
    for class_idx in sorted(class_counts.keys()):
        class_name = CLASS_MAPPING[class_idx]
        count = class_counts[class_idx]
        print(f"  {class_idx}: {class_name}: {count} файлов")
    
    print("\n✅ Датасет подготовлен!")
    print(f"📁 Путь: {YOLO_DATASET_DIR.absolute()}")
    print(f"📄 Конфиг: {yaml_path}")
    
    return True


if __name__ == '__main__':
    success = prepare_yolo_dataset()
    if success:
        print("\n✅ Готово к обучению!")
    else:
        print("\n❌ Ошибка подготовки датасета")

