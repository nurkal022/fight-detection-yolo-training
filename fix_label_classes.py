#!/usr/bin/env python3
"""
Исправление меток с неправильным классом 9
"""

from pathlib import Path

YOLO_DATASET_DIR = Path('yolo_dataset')

def fix_label_classes():
    """Исправить класс 9 на правильный класс"""
    
    print("="*60)
    print("ИСПРАВЛЕНИЕ МЕТОК С КЛАССОМ 9")
    print("="*60)
    
    fixed_count = 0
    
    # Проверяем train и val
    for split in ['train', 'val']:
        labels_dir = YOLO_DATASET_DIR / 'labels' / split
        
        if not labels_dir.exists():
            continue
        
        print(f"\n📁 Обрабатываю {split}...")
        
        for label_file in labels_dir.glob('*.txt'):
            try:
                with open(label_file, 'r') as f:
                    lines = f.readlines()
                
                modified = False
                new_lines = []
                
                for line in lines:
                    parts = line.strip().split()
                    if parts:
                        class_idx = int(parts[0])
                        
                        # Если класс 9, заменяем на 8 (neutral_class)
                        if class_idx == 9:
                            parts[0] = '8'
                            modified = True
                            fixed_count += 1
                        
                        new_lines.append(' '.join(parts) + '\n')
                
                if modified:
                    with open(label_file, 'w') as f:
                        f.writelines(new_lines)
                    
            except Exception as e:
                print(f"⚠️  Ошибка обработки {label_file.name}: {e}")
    
    print(f"\n✅ Исправлено меток: {fixed_count}")
    print("="*60)


if __name__ == '__main__':
    fix_label_classes()

