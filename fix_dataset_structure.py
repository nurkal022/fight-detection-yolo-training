#!/usr/bin/env python3
"""
Исправление структуры датасета:
- Проверяет соответствие класса в метке папке
- Переносит файлы в правильные папки
- Переименовывает файлы для удобства
"""

import shutil
from pathlib import Path
from collections import defaultdict

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

DATASET_DIR = Path('dataset')

def get_class_from_label(label_file):
    """Получить класс из файла метки (берем первый класс, если несколько объектов)"""
    try:
        with open(label_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line:
                    parts = line.split()
                    if parts:
                        return int(parts[0])
    except Exception as e:
        print(f"⚠️  Ошибка чтения {label_file}: {e}")
    return None

def fix_dataset_structure():
    """Исправить структуру датасета"""
    
    # Статистика
    stats = {
        'correct': 0,
        'moved': 0,
        'errors': 0,
        'no_label': 0,
        'by_class': defaultdict(int)
    }
    
    # Создаем все папки классов
    for class_idx, class_name in CLASS_MAPPING.items():
        (DATASET_DIR / class_name).mkdir(exist_ok=True)
    
    # Собираем все изображения с метками
    all_files = []
    
    print("📋 Сканирую датасет...")
    for class_dir in DATASET_DIR.iterdir():
        if not class_dir.is_dir() or class_dir.name not in CLASS_MAPPING.values():
            continue
        
        for img_file in class_dir.glob('*.jpg'):
            label_file = class_dir / f"{img_file.stem}.txt"
            
            if not label_file.exists():
                # Проверяем другие расширения
                label_file = class_dir / f"{img_file.stem}.txt"
                if not label_file.exists():
                    stats['no_label'] += 1
                    print(f"⚠️  Нет метки для {img_file.name}")
                    continue
            
            all_files.append((img_file, label_file, class_dir.name))
    
    print(f"✅ Найдено файлов: {len(all_files)}")
    print("\n🔍 Проверяю соответствие классов...")
    
    # Обрабатываем каждый файл
    for img_file, label_file, current_folder in all_files:
        class_idx = get_class_from_label(label_file)
        
        if class_idx is None:
            stats['errors'] += 1
            continue
        
        expected_folder = CLASS_MAPPING.get(class_idx)
        
        if expected_folder is None:
            print(f"⚠️  Неизвестный класс {class_idx} в {label_file}")
            stats['errors'] += 1
            continue
        
        # Определяем базовое имя файла (без префикса класса, если есть)
        base_img_name = img_file.name
        if base_img_name.startswith(f"{class_idx:02d}_"):
            base_img_name = base_img_name[3:]  # Убираем префикс "XX_"
        
        base_label_name = label_file.name
        if base_label_name.startswith(f"{class_idx:02d}_"):
            base_label_name = base_label_name[3:]
        
        # Новое имя файла: class_idx_original_name
        new_img_name = f"{class_idx:02d}_{base_img_name}"
        new_label_name = f"{class_idx:02d}_{base_label_name}"
        
        # Проверяем, нужно ли перемещать
        if current_folder == expected_folder:
            # Файл в правильной папке, но может быть не переименован
            target_dir = DATASET_DIR / expected_folder
            
            if img_file.name != new_img_name:
                # Нужно переименовать
                try:
                    img_file.rename(target_dir / new_img_name)
                    label_file.rename(target_dir / new_label_name)
                    if stats['correct'] % 50 == 0:
                        print(f"  Переименовано: {stats['correct']}")
                except Exception as e:
                    print(f"⚠️  Ошибка переименования {img_file.name}: {e}")
            
            stats['correct'] += 1
            stats['by_class'][class_idx] += 1
        else:
            # Нужно переместить
            target_dir = DATASET_DIR / expected_folder
            
            target_img = target_dir / new_img_name
            target_label = target_dir / new_label_name
            
            # Проверяем, не существует ли уже файл с таким именем
            if target_img.exists():
                print(f"⚠️  Файл уже существует: {target_img.name}, пропускаю")
                stats['errors'] += 1
                continue
            
            try:
                # Перемещаем изображение
                shutil.move(str(img_file), str(target_img))
                
                # Перемещаем и переименовываем метку
                shutil.move(str(label_file), str(target_label))
                
                stats['moved'] += 1
                stats['by_class'][class_idx] += 1
                
                if stats['moved'] % 20 == 0:
                    print(f"  Перемещено: {stats['moved']}")
                    
            except Exception as e:
                print(f"❌ Ошибка перемещения {img_file.name}: {e}")
                stats['errors'] += 1
    
    
    # Итоговая статистика
    print("\n" + "="*60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*60)
    print(f"✅ Правильно расположено: {stats['correct']}")
    print(f"🔄 Перемещено: {stats['moved']}")
    print(f"⚠️  Без меток: {stats['no_label']}")
    print(f"❌ Ошибок: {stats['errors']}")
    print("\n📦 По классам:")
    for class_idx in sorted(stats['by_class'].keys()):
        class_name = CLASS_MAPPING[class_idx]
        count = stats['by_class'][class_idx]
        print(f"  {class_idx}: {class_name}: {count} файлов")
    
    # Финальный подсчет
    print("\n📊 Финальное количество файлов:")
    for class_idx, class_name in CLASS_MAPPING.items():
        class_dir = DATASET_DIR / class_name
        images = list(class_dir.glob('*.jpg'))
        labels = list(class_dir.glob('*.txt'))
        print(f"  {class_name}: {len(images)} изображений, {len(labels)} меток")
    
    print("="*60)


if __name__ == '__main__':
    print("="*60)
    print("ИСПРАВЛЕНИЕ СТРУКТУРЫ ДАТАСЕТА")
    print("="*60)
    print("\nЭто скрипт:")
    print("1. Проверит соответствие классов в метках папкам")
    print("2. Переместит файлы в правильные папки")
    print("3. Переименует файлы в формат: class_idx_filename.jpg")
    print()
    
    response = input("⚠️  Продолжить? (yes/no): ")
    if response.lower() != 'yes':
        print("Отменено.")
        exit(0)
    
    fix_dataset_structure()
    print("\n✅ Готово!")

