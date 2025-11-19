#!/usr/bin/env python3
"""
Скрипт для синхронизации меток с изображениями датасета

Объединяет метки из папки labels с изображениями в dataset:
- Копирует метки рядом с соответствующими изображениями
- Удаляет изображения, для которых нет меток
"""

import os
import shutil
from pathlib import Path

# Пути
DATASET_DIR = Path('dataset')
LABELS_DIR = Path('labels_my-project-name_2025-11-19-03-14-42')

def sync_labels():
    """Синхронизировать метки с изображениями"""
    
    if not LABELS_DIR.exists():
        print(f"❌ Папка с метками не найдена: {LABELS_DIR}")
        return
    
    if not DATASET_DIR.exists():
        print(f"❌ Папка датасета не найдена: {DATASET_DIR}")
        return
    
    # Собираем все метки
    print("📋 Сканирую метки...")
    labels_files = {}
    for label_file in LABELS_DIR.glob('*.txt'):
        # Имя файла метки должно соответствовать имени изображения
        label_name = label_file.stem  # без расширения
        
        # Пропускаем файлы типа "2.txt"
        if label_name.isdigit():
            print(f"⚠️  Пропущен файл с числовым именем: {label_file.name}")
            continue
        
        labels_files[label_name] = label_file
    
    print(f"✅ Найдено меток: {len(labels_files)}")
    
    # Статистика
    stats = {
        'copied': 0,
        'deleted': 0,
        'not_found': 0,
        'errors': 0
    }
    
    # Обрабатываем каждую папку класса
    print("\n📁 Обработка классов...")
    for class_dir in DATASET_DIR.iterdir():
        if not class_dir.is_dir():
            continue
        
        class_name = class_dir.name
        print(f"\n  Класс: {class_name}")
        
        # Находим все изображения в папке класса
        images = list(class_dir.glob('*.jpg')) + list(class_dir.glob('*.jpeg')) + list(class_dir.glob('*.png'))
        
        for img_file in images:
            img_name = img_file.stem  # имя без расширения
            
            # Ищем соответствующую метку
            if img_name in labels_files:
                # Копируем метку рядом с изображением
                label_source = labels_files[img_name]
                label_dest = class_dir / f"{img_name}.txt"
                
                try:
                    shutil.copy2(label_source, label_dest)
                    stats['copied'] += 1
                    if stats['copied'] % 50 == 0:
                        print(f"    Скопировано меток: {stats['copied']}")
                except Exception as e:
                    print(f"    ❌ Ошибка копирования {label_source.name}: {e}")
                    stats['errors'] += 1
            else:
                # Удаляем изображение без метки
                try:
                    img_file.unlink()
                    stats['deleted'] += 1
                    if stats['deleted'] % 50 == 0:
                        print(f"    Удалено изображений: {stats['deleted']}")
                except Exception as e:
                    print(f"    ❌ Ошибка удаления {img_file.name}: {e}")
                    stats['errors'] += 1
    
    # Проверяем метки без изображений
    print("\n🔍 Проверка меток без изображений...")
    for label_name, label_file in labels_files.items():
        # Ищем класс по префиксу имени файла
        class_name = label_name.split('_')[0]
        class_dir = DATASET_DIR / class_name
        
        if not class_dir.exists():
            stats['not_found'] += 1
            if stats['not_found'] <= 10:  # Показываем первые 10
                print(f"  ⚠️  Метка без класса: {label_name} (класс: {class_name})")
            continue
        
        img_file = class_dir / f"{label_name}.jpg"
        if not img_file.exists():
            img_file = class_dir / f"{label_name}.jpeg"
        if not img_file.exists():
            img_file = class_dir / f"{label_name}.png"
        
        if not img_file.exists():
            stats['not_found'] += 1
            if stats['not_found'] <= 10:  # Показываем первые 10
                print(f"  ⚠️  Метка без изображения: {label_name}")
    
    # Итоговая статистика
    print("\n" + "="*60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("="*60)
    print(f"✅ Скопировано меток: {stats['copied']}")
    print(f"🗑️  Удалено изображений без меток: {stats['deleted']}")
    print(f"⚠️  Меток без изображений: {stats['not_found']}")
    print(f"❌ Ошибок: {stats['errors']}")
    print("="*60)
    
    # Подсчет финального количества изображений
    total_images = 0
    for class_dir in DATASET_DIR.iterdir():
        if class_dir.is_dir():
            images = list(class_dir.glob('*.jpg')) + list(class_dir.glob('*.jpeg')) + list(class_dir.glob('*.png'))
            total_images += len(images)
            print(f"  {class_dir.name}: {len(images)} изображений")
    
    print(f"\n📦 Всего изображений в датасете: {total_images}")


if __name__ == '__main__':
    print("="*60)
    print("СИНХРОНИЗАЦИЯ МЕТОК С ИЗОБРАЖЕНИЯМИ")
    print("="*60)
    print()
    
    response = input("⚠️  Это удалит изображения без меток. Продолжить? (yes/no): ")
    if response.lower() != 'yes':
        print("Отменено.")
        exit(0)
    
    sync_labels()
    print("\n✅ Готово!")

