#!/usr/bin/env python3
"""
Dataset Collection Tool
Консольная программа для сбора датасета через веб-камеру

Использование:
    python collect_dataset.py
"""

import cv2
import os
import json
import time
import sys
from datetime import datetime
from pathlib import Path

# Конфигурация
DATASET_DIR = 'dataset'
PROGRESS_FILE = 'dataset_progress.json'
CLASSES_FILE = 'dataset_classes.json'
AUTO_INTERVAL = 3  # секунды для автоматического режима


class DatasetCollector:
    def __init__(self):
        self.dataset_dir = Path(DATASET_DIR)
        self.progress_file = Path(PROGRESS_FILE)
        self.camera = None
        self.progress = self.load_progress()
        
    def load_progress(self):
        """Загрузить прогресс из файла"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Ошибка загрузки прогресса: {e}")
                return {}
        return {}
    
    def save_progress(self):
        """Сохранить прогресс в файл"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Ошибка сохранения прогресса: {e}")
    
    def load_classes_from_file(self):
        """Загрузить классы из JSON файла"""
        classes_file = Path(CLASSES_FILE)
        
        if not classes_file.exists():
            print(f"\n❌ Файл {CLASSES_FILE} не найден!")
            print(f"   Создайте файл {CLASSES_FILE} с форматом:")
            print("""
{
  "classes": [
    {
      "name": "class1",
      "target": 100,
      "description": "Описание класса"
    }
  ]
}
""")
            return None
        
        try:
            with open(classes_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if 'classes' not in config:
                print(f"\n❌ Неверный формат файла {CLASSES_FILE}!")
                print("   Ожидается поле 'classes'")
                return None
            
            classes_config = {}
            for cls in config['classes']:
                if 'name' not in cls or 'target' not in cls:
                    print(f"⚠️  Пропущен класс без 'name' или 'target'")
                    continue
                
                classes_config[cls['name']] = {
                    'target': int(cls['target']),
                    'collected': 0,
                    'description': cls.get('description', '')
                }
            
            if not classes_config:
                print(f"\n❌ Не найдено ни одного валидного класса в {CLASSES_FILE}!")
                return None
            
            return classes_config
            
        except json.JSONDecodeError as e:
            print(f"\n❌ Ошибка парсинга JSON в {CLASSES_FILE}: {e}")
            return None
        except Exception as e:
            print(f"\n❌ Ошибка загрузки {CLASSES_FILE}: {e}")
            return None
    
    def get_classes_config(self):
        """Получить конфигурацию классов"""
        print("\n" + "="*60)
        print("НАСТРОЙКА СБОРА ДАТАСЕТА")
        print("="*60)
        
        # Загружаем классы из файла
        classes_config = self.load_classes_from_file()
        if not classes_config:
            return None
        
        print(f"\n📋 Загружено классов из {CLASSES_FILE}: {len(classes_config)}")
        for class_name, class_data in classes_config.items():
            desc = class_data.get('description', '')
            desc_text = f" - {desc}" if desc else ""
            print(f"  • {class_name}: {class_data['target']} изображений{desc_text}")
        
        # Проверяем сохраненный прогресс
        if self.progress and 'classes' in self.progress:
            print("\n📋 Найден сохраненный прогресс:")
            has_progress = False
            for class_name, class_data in self.progress['classes'].items():
                if class_name in classes_config:
                    collected = class_data.get('collected', 0)
                    target = class_data.get('target', classes_config[class_name]['target'])
                    if collected > 0:
                        has_progress = True
                        print(f"  • {class_name}: {collected}/{target} изображений")
            
            if has_progress:
                resume = input("\n❓ Продолжить с сохраненного прогресса? (y/n): ").strip().lower()
                if resume == 'y':
                    # Объединяем прогресс с конфигурацией из файла
                    for class_name in classes_config:
                        if class_name in self.progress.get('classes', {}):
                            saved_data = self.progress['classes'][class_name]
                            classes_config[class_name]['collected'] = saved_data.get('collected', 0)
                            # Обновляем target из файла, если изменился
                            classes_config[class_name]['target'] = classes_config[class_name]['target']
                    return classes_config
        
        # Сохраняем конфигурацию в прогресс
        self.progress = {
            'classes': {name: {'target': data['target'], 'collected': data['collected']} 
                       for name, data in classes_config.items()}
        }
        self.save_progress()
        
        return classes_config
    
    def select_mode(self):
        """Выбрать режим сбора"""
        print("\n" + "="*60)
        print("ВЫБОР РЕЖИМА")
        print("="*60)
        print("1. Автоматический режим (каждые 3 секунды)")
        print("2. Ручной режим (нажмите ПРОБЕЛ для фото)")
        print()
        
        while True:
            choice = input("Выберите режим (1 или 2): ").strip()
            if choice == '1':
                return 'auto'
            elif choice == '2':
                return 'manual'
            else:
                print("⚠️  Введите 1 или 2!")
    
    def init_camera(self):
        """Инициализировать камеру"""
        print("\n📹 Инициализация камеры...")
        
        # Пробуем разные индексы камер
        for camera_idx in range(3):
            self.camera = cv2.VideoCapture(camera_idx)
            if self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    print(f"✅ Камера {camera_idx} успешно инициализирована")
                    return True
                self.camera.release()
        
        print("❌ Не удалось открыть камеру!")
        return False
    
    def capture_image(self, class_name, class_dir):
        """Сделать снимок и сохранить"""
        ret, frame = self.camera.read()
        if not ret or frame is None:
            return False
        
        # Генерируем имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f"{class_name}_{timestamp}.jpg"
        filepath = class_dir / filename
        
        # Сохраняем изображение
        cv2.imwrite(str(filepath), frame)
        return True
    
    def collect_class_auto(self, class_name, class_data):
        """Собрать данные для класса в автоматическом режиме"""
        class_dir = self.dataset_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        
        target = class_data['target']
        collected = class_data['collected']
        remaining = target - collected
        
        if remaining <= 0:
            print(f"\n✅ Класс '{class_name}' уже собран полностью!")
            return True
        
        print(f"\n{'='*60}")
        print(f"СБОР ДАННЫХ: {class_name}")
        print(f"{'='*60}")
        print(f"Цель: {target} изображений")
        print(f"Уже собрано: {collected}")
        print(f"Осталось: {remaining}")
        print(f"Режим: Автоматический (каждые {AUTO_INTERVAL} сек)")
        print(f"\nНажмите 'q' для выхода или 's' для пропуска класса")
        print("Нажмите Enter для начала...")
        input()
        
        count = 0
        last_capture_time = time.time()
        
        while collected < target:
            ret, frame = self.camera.read()
            if not ret:
                print("❌ Ошибка чтения кадра!")
                break
            
            # Показываем кадр
            display_frame = frame.copy()
            cv2.putText(display_frame, f"{class_name}: {collected + 1}/{target}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Next capture in: {int(AUTO_INTERVAL - (time.time() - last_capture_time))}s", 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            cv2.imshow('Dataset Collection - Auto Mode', display_frame)
            
            # Проверяем нажатия клавиш
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n⏸️  Сбор прерван пользователем")
                break
            elif key == ord('s'):
                print(f"\n⏭️  Пропуск класса '{class_name}'")
                break
            
            # Автоматический захват каждые 3 секунды
            if time.time() - last_capture_time >= AUTO_INTERVAL:
                if self.capture_image(class_name, class_dir):
                    collected += 1
                    count += 1
                    self.progress['classes'][class_name]['collected'] = collected
                    self.save_progress()
                    
                    print(f"📸 [{collected}/{target}] Сохранено: {class_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                    last_capture_time = time.time()
        
        cv2.destroyAllWindows()
        return collected >= target
    
    def collect_class_manual(self, class_name, class_data):
        """Собрать данные для класса в ручном режиме"""
        class_dir = self.dataset_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        
        target = class_data['target']
        collected = class_data['collected']
        remaining = target - collected
        
        if remaining <= 0:
            print(f"\n✅ Класс '{class_name}' уже собран полностью!")
            return True
        
        print(f"\n{'='*60}")
        print(f"СБОР ДАННЫХ: {class_name}")
        print(f"{'='*60}")
        print(f"Цель: {target} изображений")
        print(f"Уже собрано: {collected}")
        print(f"Осталось: {remaining}")
        print(f"Режим: Ручной")
        print(f"\nУправление:")
        print(f"  ПРОБЕЛ - сделать фото")
        print(f"  'q' - выйти")
        print(f"  's' - пропустить класс")
        print(f"\nНажмите Enter для начала...")
        input()
        
        while collected < target:
            ret, frame = self.camera.read()
            if not ret:
                print("❌ Ошибка чтения кадра!")
                break
            
            # Показываем кадр
            display_frame = frame.copy()
            cv2.putText(display_frame, f"{class_name}: {collected + 1}/{target}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(display_frame, "Press SPACE to capture", 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            cv2.imshow('Dataset Collection - Manual Mode', display_frame)
            
            # Проверяем нажатия клавиш
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n⏸️  Сбор прерван пользователем")
                break
            elif key == ord('s'):
                print(f"\n⏭️  Пропуск класса '{class_name}'")
                break
            elif key == ord(' '):  # Пробел
                if self.capture_image(class_name, class_dir):
                    collected += 1
                    self.progress['classes'][class_name]['collected'] = collected
                    self.save_progress()
                    
                    print(f"📸 [{collected}/{target}] Сохранено: {class_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                    
                    # Мигание экрана для подтверждения
                    cv2.putText(display_frame, "CAPTURED!", 
                               (display_frame.shape[1]//2 - 100, display_frame.shape[0]//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
                    cv2.imshow('Dataset Collection - Manual Mode', display_frame)
                    cv2.waitKey(200)
        
        cv2.destroyAllWindows()
        return collected >= target
    
    def run(self):
        """Запустить сбор датасета"""
        print("\n" + "="*60)
        print("ИНСТРУМЕНТ СБОРА ДАТАСЕТА")
        print("="*60)
        
        # Получаем конфигурацию классов
        classes_config = self.get_classes_config()
        if not classes_config:
            print("\n❌ Конфигурация не создана. Выход.")
            return
        
        # Выбираем режим
        mode = self.select_mode()
        
        # Инициализируем камеру
        if not self.init_camera():
            return
        
        try:
            # Собираем данные для каждого класса
            for class_name, class_data in classes_config.items():
                if mode == 'auto':
                    self.collect_class_auto(class_name, class_data)
                else:
                    self.collect_class_manual(class_name, class_data)
                
                # Проверяем, все ли классы собраны
                all_complete = all(
                    c['collected'] >= c['target'] 
                    for c in classes_config.values()
                )
                
                if all_complete:
                    print("\n" + "="*60)
                    print("✅ ВСЕ КЛАССЫ СОБРАНЫ!")
                    print("="*60)
                    break
            
            # Показываем итоговую статистику
            print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
            print("-" * 60)
            total_collected = 0
            total_target = 0
            
            for class_name, class_data in classes_config.items():
                collected = class_data['collected']
                target = class_data['target']
                total_collected += collected
                total_target += target
                
                status = "✅" if collected >= target else "⏳"
                print(f"{status} {class_name}: {collected}/{target}")
            
            print("-" * 60)
            print(f"Всего: {total_collected}/{total_target}")
            print(f"\n💾 Данные сохранены в: {self.dataset_dir.absolute()}")
            print(f"💾 Прогресс сохранен в: {self.progress_file.absolute()}")
            
        except KeyboardInterrupt:
            print("\n\n⏸️  Сбор прерван пользователем (Ctrl+C)")
            print("💾 Прогресс сохранен. Можно продолжить позже.")
        finally:
            if self.camera:
                self.camera.release()
            cv2.destroyAllWindows()


def main():
    collector = DatasetCollector()
    collector.run()


if __name__ == '__main__':
    main()

