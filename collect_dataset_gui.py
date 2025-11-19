#!/usr/bin/env python3
"""
Dataset Collection Tool - GUI Version
Нативная программа с графическим интерфейсом на pygame для сбора датасета

Использование:
    python collect_dataset_gui.py
"""

import pygame
import cv2
import numpy as np
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock

# Конфигурация
DATASET_DIR = 'dataset'
PROGRESS_FILE = 'dataset_progress.json'
CLASSES_FILE = 'dataset_classes.json'
AUTO_INTERVAL = 1  # секунды для автоматического режима
ROTATE_FRAME = False  # Поворачивать ли кадр на 90 градусов (для некоторых камер на macOS)

# Цвета
COLOR_BG = (30, 30, 30)
COLOR_PANEL = (40, 40, 40)
COLOR_TEXT = (255, 255, 255)
COLOR_SUCCESS = (76, 175, 80)
COLOR_WARNING = (255, 152, 0)
COLOR_ERROR = (244, 67, 54)
COLOR_PRIMARY = (33, 150, 243)
COLOR_SECONDARY = (156, 39, 176)

# Размеры окна
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
VIDEO_WIDTH = 960
VIDEO_HEIGHT = 540
PANEL_WIDTH = WINDOW_WIDTH - VIDEO_WIDTH


class DatasetCollectorGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Dataset Collection Tool")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        
        self.dataset_dir = Path(DATASET_DIR)
        self.progress_file = Path(PROGRESS_FILE)
        self.classes_file = Path(CLASSES_FILE)
        
        self.camera = None
        self.current_frame = None
        self.frame_lock = Lock()
        self.camera_running = False
        
        self.classes_config = {}
        self.progress = {}
        self.current_class_index = 0
        self.mode = 'manual'  # 'auto' or 'manual'
        self.running = True
        self.capturing = False
        self.last_capture_time = 0
        self.capture_flash = False
        self.flash_time = 0
        self.hovered_button = None
        
        self.load_config()
        if not self.init_camera():
            print("⚠️  Программа запустится без камеры. Вы сможете использовать интерфейс, но видео не будет отображаться.")
    
    def load_config(self):
        """Загрузить конфигурацию классов и прогресс"""
        # Загружаем классы
        if not self.classes_file.exists():
            print(f"❌ Файл {CLASSES_FILE} не найден!")
            sys.exit(1)
        
        try:
            with open(self.classes_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            for cls in config.get('classes', []):
                self.classes_config[cls['name']] = {
                    'target': int(cls['target']),
                    'collected': 0,
                    'description': cls.get('description', '')
                }
        except Exception as e:
            print(f"❌ Ошибка загрузки классов: {e}")
            sys.exit(1)
        
        # Загружаем прогресс
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    saved_progress = json.load(f)
                
                for class_name, class_data in saved_progress.get('classes', {}).items():
                    if class_name in self.classes_config:
                        self.classes_config[class_name]['collected'] = class_data.get('collected', 0)
            except Exception as e:
                print(f"⚠️  Ошибка загрузки прогресса: {e}")
        
        self.save_progress()
    
    def save_progress(self):
        """Сохранить прогресс"""
        progress = {
            'classes': {
                name: {
                    'target': data['target'],
                    'collected': data['collected']
                }
                for name, data in self.classes_config.items()
            }
        }
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Ошибка сохранения прогресса: {e}")
    
    def init_camera(self):
        """Инициализировать камеру"""
        try:
            for camera_idx in range(3):
                try:
                    self.camera = cv2.VideoCapture(camera_idx)
                    if self.camera.isOpened():
                        ret, frame = self.camera.read()
                        if ret and frame is not None:
                            self.camera_running = True
                            # Запускаем поток чтения кадров
                            Thread(target=self.camera_thread, daemon=True).start()
                            print(f"✅ Камера {camera_idx} успешно инициализирована")
                            return True
                        self.camera.release()
                except Exception as e:
                    print(f"⚠️  Ошибка при открытии камеры {camera_idx}: {e}")
                    if self.camera:
                        self.camera.release()
                    continue
            
            print("❌ Не удалось открыть камеру!")
            return False
        except Exception as e:
            print(f"❌ Критическая ошибка инициализации камеры: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def camera_thread(self):
        """Поток для чтения кадров с камеры"""
        try:
            while self.camera_running and self.camera:
                try:
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        # Конвертируем BGR в RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # Получаем размеры кадра
                        height, width = frame_rgb.shape[:2]
                        
                        # Масштабируем с сохранением пропорций
                        scale = min(VIDEO_WIDTH / width, VIDEO_HEIGHT / height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        
                        # Изменяем размер кадра
                        frame_resized = cv2.resize(frame_rgb, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                        
                        # Поворачиваем кадр если нужно (для некоторых камер на macOS)
                        if ROTATE_FRAME:
                            frame_resized = np.rot90(frame_resized, -1)
                            # После поворота меняем размеры местами
                            new_width, new_height = new_height, new_width
                        
                        # Конвертируем numpy array в pygame surface
                        try:
                            # Транспонируем массив (pygame ожидает формат (width, height))
                            frame_surface = pygame.surfarray.make_surface(frame_resized.swapaxes(0, 1))
                            
                            # Создаем финальный кадр с правильным размером
                            final_frame = pygame.Surface((VIDEO_WIDTH, VIDEO_HEIGHT))
                            final_frame.fill((0, 0, 0))  # Черный фон
                            
                            # Центрируем кадр
                            x_offset = (VIDEO_WIDTH - new_width) // 2
                            y_offset = (VIDEO_HEIGHT - new_height) // 2
                            final_frame.blit(frame_surface, (x_offset, y_offset))
                            
                            with self.frame_lock:
                                self.current_frame = final_frame
                        except Exception as e:
                            print(f"Ошибка конвертации кадра в pygame surface: {e}")
                            time.sleep(0.1)
                except Exception as e:
                    print(f"Ошибка обработки кадра: {e}")
                    time.sleep(0.1)
                
                time.sleep(0.033)  # ~30 FPS
        except Exception as e:
            print(f"Критическая ошибка в потоке камеры: {e}")
            import traceback
            traceback.print_exc()
    
    def capture_image(self):
        """Сделать снимок текущего кадра"""
        if not self.current_frame:
            return False
        
        # Получаем текущий класс
        class_names = list(self.classes_config.keys())
        if self.current_class_index >= len(class_names):
            return False
        
        class_name = class_names[self.current_class_index]
        class_data = self.classes_config[class_name]
        
        if class_data['collected'] >= class_data['target']:
            return False
        
        # Сохраняем кадр
        class_dir = self.dataset_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        
        # Получаем кадр из камеры напрямую
        ret, frame = self.camera.read()
        if not ret:
            return False
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f"{class_name}_{timestamp}.jpg"
        filepath = class_dir / filename
        
        cv2.imwrite(str(filepath), frame)
        
        # Обновляем прогресс
        class_data['collected'] += 1
        self.save_progress()
        
        # Визуальный эффект захвата
        self.capture_flash = True
        self.flash_time = time.time()
        
        return True
    
    def draw_text(self, surface, text, pos, font, color=COLOR_TEXT, center=False):
        """Отрисовать текст"""
        text_surface = font.render(str(text), True, color)
        if center:
            pos = (pos[0] - text_surface.get_width() // 2, pos[1])
        surface.blit(text_surface, pos)
        return text_surface.get_height()
    
    def draw_button(self, pos, size, text, color, enabled=True, button_id=None):
        """Отрисовать кнопку и вернуть её rect"""
        x, y = pos
        width, height = size
        
        # Проверяем наведение мыши
        mouse_pos = pygame.mouse.get_pos()
        button_rect = pygame.Rect(x, y, width, height)
        is_hovered = button_rect.collidepoint(mouse_pos) and enabled
        
        if button_id:
            if is_hovered:
                self.hovered_button = button_id
        
        # Создаем поверхность для кнопки
        button_surface = pygame.Surface((width, height))
        
        if enabled:
            # Усиливаем цвет при наведении
            if is_hovered:
                # Делаем цвет ярче
                bright_color = tuple(min(255, c + 30) for c in color)
                pygame.draw.rect(button_surface, bright_color, (0, 0, width, height))
            else:
                pygame.draw.rect(button_surface, color, (0, 0, width, height))
            
            # Рамка (более яркая при наведении)
            border_color = (255, 255, 255) if is_hovered else (200, 200, 200)
            pygame.draw.rect(button_surface, border_color, (0, 0, width, height), 2)
            
            # Текст
            text_surface = self.font_small.render(text, True, COLOR_TEXT)
            text_x = (width - text_surface.get_width()) // 2
            text_y = (height - text_surface.get_height()) // 2
            button_surface.blit(text_surface, (text_x, text_y))
        else:
            # Отключенная кнопка
            pygame.draw.rect(button_surface, (60, 60, 60), (0, 0, width, height))
            pygame.draw.rect(button_surface, (100, 100, 100), (0, 0, width, height), 2)
            text_surface = self.font_small.render(text, True, (150, 150, 150))
            text_x = (width - text_surface.get_width()) // 2
            text_y = (height - text_surface.get_height()) // 2
            button_surface.blit(text_surface, (text_x, text_y))
        
        # Отображаем кнопку
        self.screen.blit(button_surface, pos)
        
        # Возвращаем rect для проверки клика
        return button_rect
    
    def draw_panel(self):
        """Отрисовать панель информации"""
        panel_rect = pygame.Rect(VIDEO_WIDTH, 0, PANEL_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect)
        
        y_offset = 20
        
        # Заголовок
        self.draw_text(self.screen, "Dataset Collector", (VIDEO_WIDTH + PANEL_WIDTH // 2, y_offset), 
                      self.font_large, COLOR_TEXT, center=True)
        y_offset += 60
        
        # Текущий класс
        class_names = list(self.classes_config.keys())
        if class_names:
            current_class = class_names[self.current_class_index]
            class_data = self.classes_config[current_class]
            
            # Название класса
            self.draw_text(self.screen, f"Class: {current_class}", 
                          (VIDEO_WIDTH + 20, y_offset), self.font_medium, COLOR_PRIMARY)
            y_offset += 40
            
            # Описание
            if class_data.get('description'):
                desc_lines = self.wrap_text(class_data['description'], PANEL_WIDTH - 40, self.font_small)
                for line in desc_lines:
                    self.draw_text(self.screen, line, (VIDEO_WIDTH + 20, y_offset), 
                                  self.font_small, (200, 200, 200))
                    y_offset += 25
                y_offset += 10
            
            # Прогресс
            collected = class_data['collected']
            target = class_data['target']
            progress_pct = (collected / target * 100) if target > 0 else 0
            
            self.draw_text(self.screen, f"Progress: {collected}/{target}", 
                          (VIDEO_WIDTH + 20, y_offset), self.font_medium, COLOR_TEXT)
            y_offset += 40
            
            # Прогресс-бар
            bar_width = PANEL_WIDTH - 40
            bar_height = 30
            bar_x = VIDEO_WIDTH + 20
            bar_y = y_offset
            
            # Фон прогресс-бара
            pygame.draw.rect(self.screen, (60, 60, 60), 
                          (bar_x, bar_y, bar_width, bar_height))
            
            # Заполнение прогресс-бара
            fill_width = int(bar_width * progress_pct / 100)
            color = COLOR_SUCCESS if progress_pct >= 100 else COLOR_PRIMARY
            pygame.draw.rect(self.screen, color, 
                          (bar_x, bar_y, fill_width, bar_height))
            
            # Процент
            self.draw_text(self.screen, f"{progress_pct:.1f}%", 
                          (VIDEO_WIDTH + PANEL_WIDTH // 2, bar_y + bar_height // 2), 
                          self.font_small, COLOR_TEXT, center=True)
            y_offset += 50
            
            # Режим
            mode_text = f"Auto ({AUTO_INTERVAL}s)" if self.mode == 'auto' else "Manual (SPACE)"
            mode_color = COLOR_WARNING if self.mode == 'auto' else COLOR_SECONDARY
            self.draw_text(self.screen, f"Mode: {mode_text}", 
                          (VIDEO_WIDTH + 20, y_offset), self.font_medium, mode_color)
            y_offset += 50
            
            # Автоматический режим - таймер
            if self.mode == 'auto':
                time_left = AUTO_INTERVAL - (time.time() - self.last_capture_time)
                if time_left > 0:
                    self.draw_text(self.screen, f"Next: {time_left:.1f}s", 
                                  (VIDEO_WIDTH + 20, y_offset), self.font_small, COLOR_WARNING)
                    y_offset += 30
        
        y_offset += 20
        
        # Статистика по всем классам
        self.draw_text(self.screen, "All Classes:", (VIDEO_WIDTH + 20, y_offset), 
                      self.font_medium, COLOR_TEXT)
        y_offset += 35
        
        total_collected = 0
        total_target = 0
        
        # Ограничиваем количество отображаемых классов, чтобы не перекрывать кнопки
        max_classes_display = 5
        classes_list = list(self.classes_config.items())
        
        for idx, (class_name, class_data) in enumerate(classes_list[:max_classes_display]):
            collected = class_data['collected']
            target = class_data['target']
            total_collected += collected
            total_target += target
            
            # Выделяем текущий класс
            if idx == self.current_class_index:
                pygame.draw.rect(self.screen, (60, 60, 60), 
                               (VIDEO_WIDTH + 10, y_offset - 5, PANEL_WIDTH - 20, 25))
            
            color = COLOR_SUCCESS if collected >= target else COLOR_TEXT
            status = "OK" if collected >= target else "..."
            
            text = f"{status} {class_name}: {collected}/{target}"
            self.draw_text(self.screen, text, (VIDEO_WIDTH + 20, y_offset), 
                          self.font_small, color)
            y_offset += 25
        
        # Показываем общее количество, если классов больше
        if len(classes_list) > max_classes_display:
            remaining = len(classes_list) - max_classes_display
            for class_name, class_data in classes_list[max_classes_display:]:
                total_collected += class_data['collected']
                total_target += class_data['target']
            
            self.draw_text(self.screen, f"... and {remaining} more", 
                          (VIDEO_WIDTH + 20, y_offset), self.font_small, (150, 150, 150))
            y_offset += 25
        
        y_offset += 15
        
        # Общая статистика
        total_pct = (total_collected / total_target * 100) if total_target > 0 else 0
        self.draw_text(self.screen, f"Total: {total_collected}/{total_target}", 
                      (VIDEO_WIDTH + 20, y_offset), self.font_medium, COLOR_TEXT)
        y_offset += 30
        
        # Общий прогресс-бар
        bar_width = PANEL_WIDTH - 40
        bar_height = 25
        bar_x = VIDEO_WIDTH + 20
        bar_y = y_offset
        
        pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
        fill_width = int(bar_width * total_pct / 100)
        pygame.draw.rect(self.screen, COLOR_SUCCESS if total_pct >= 100 else COLOR_PRIMARY, 
                       (bar_x, bar_y, fill_width, bar_height))
        
        self.draw_text(self.screen, f"{total_pct:.1f}%", 
                      (VIDEO_WIDTH + PANEL_WIDTH // 2, bar_y + bar_height // 2), 
                      self.font_small, COLOR_TEXT, center=True)
        
        # Кнопки управления - фиксированная позиция снизу
        y_offset = WINDOW_HEIGHT - 200
        
        self.draw_text(self.screen, "Controls:", (VIDEO_WIDTH + 20, y_offset), 
                      self.font_medium, COLOR_TEXT)
        y_offset += 40
        
        # Кнопка Capture
        capture_btn = self.draw_button(
            (VIDEO_WIDTH + 20, y_offset), 
            (PANEL_WIDTH - 40, 40),
            "Capture", 
            COLOR_PRIMARY if self.mode == 'manual' else (100, 100, 100),
            self.mode == 'manual',
            'capture'
        )
        self.capture_button_rect = capture_btn
        y_offset += 50
        
        # Кнопки режимов
        auto_btn = self.draw_button(
            (VIDEO_WIDTH + 20, y_offset), 
            ((PANEL_WIDTH - 50) // 2, 35),
            "Auto", 
            COLOR_WARNING if self.mode == 'auto' else (80, 80, 80),
            True,
            'auto'
        )
        self.auto_button_rect = auto_btn
        
        manual_btn = self.draw_button(
            (VIDEO_WIDTH + 30 + (PANEL_WIDTH - 50) // 2, y_offset), 
            ((PANEL_WIDTH - 50) // 2, 35),
            "Manual", 
            COLOR_SECONDARY if self.mode == 'manual' else (80, 80, 80),
            True,
            'manual'
        )
        self.manual_button_rect = manual_btn
        y_offset += 45
        
        # Кнопки навигации по классам
        prev_btn = self.draw_button(
            (VIDEO_WIDTH + 20, y_offset), 
            ((PANEL_WIDTH - 50) // 2, 35),
            "Prev", 
            (100, 150, 200),
            True,
            'prev'
        )
        self.prev_button_rect = prev_btn
        
        next_btn = self.draw_button(
            (VIDEO_WIDTH + 30 + (PANEL_WIDTH - 50) // 2, y_offset), 
            ((PANEL_WIDTH - 50) // 2, 35),
            "Next", 
            (100, 150, 200),
            True,
            'next'
        )
        self.next_button_rect = next_btn
        y_offset += 45
        
        # Кнопка выхода
        quit_btn = self.draw_button(
            (VIDEO_WIDTH + 20, y_offset), 
            (PANEL_WIDTH - 40, 35),
            "Quit", 
            COLOR_ERROR,
            True,
            'quit'
        )
        self.quit_button_rect = quit_btn
    
    def wrap_text(self, text, max_width, font):
        """Переносить текст по словам"""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def draw_video(self):
        """Отрисовать видео"""
        video_rect = pygame.Rect(0, 0, VIDEO_WIDTH, VIDEO_HEIGHT)
        pygame.draw.rect(self.screen, (0, 0, 0), video_rect)
        
        try:
            with self.frame_lock:
                if self.current_frame:
                    self.screen.blit(self.current_frame, (0, 0))
        except Exception as e:
            # Если ошибка при отрисовке кадра, просто пропускаем
            pass
        
        # Наложение информации на видео
        try:
            class_names = list(self.classes_config.keys())
            if class_names:
                current_class = class_names[self.current_class_index]
                class_data = self.classes_config[current_class]
                
                # Название класса вверху
                text = f"{current_class} ({class_data['collected']}/{class_data['target']})"
                text_surface = self.font_medium.render(text, True, COLOR_TEXT)
                bg_rect = pygame.Rect(10, 10, text_surface.get_width() + 20, text_surface.get_height() + 10)
                pygame.draw.rect(self.screen, (0, 0, 0, 180), bg_rect)
                self.screen.blit(text_surface, (20, 15))
                
                # Режим
                mode_text = "AUTO" if self.mode == 'auto' else "MANUAL"
                mode_surface = self.font_small.render(mode_text, True, COLOR_WARNING if self.mode == 'auto' else COLOR_SECONDARY)
                bg_rect = pygame.Rect(10, 50, mode_surface.get_width() + 20, mode_surface.get_height() + 10)
                pygame.draw.rect(self.screen, (0, 0, 0, 180), bg_rect)
                self.screen.blit(mode_surface, (20, 55))
        except:
            pass
        
        # Эффект вспышки при захвате
        if self.capture_flash:
            if time.time() - self.flash_time < 0.2:
                overlay = pygame.Surface((VIDEO_WIDTH, VIDEO_HEIGHT))
                overlay.set_alpha(100)
                overlay.fill((255, 255, 255))
                self.screen.blit(overlay, (0, 0))
            else:
                self.capture_flash = False
    
    def next_class(self):
        """Перейти к следующему классу"""
        self.current_class_index = (self.current_class_index + 1) % len(self.classes_config)
        self.last_capture_time = time.time()
    
    def prev_class(self):
        """Перейти к предыдущему классу"""
        self.current_class_index = (self.current_class_index - 1) % len(self.classes_config)
        self.last_capture_time = time.time()
    
    def toggle_mode(self):
        """Переключить режим"""
        self.mode = 'auto' if self.mode == 'manual' else 'manual'
        self.last_capture_time = time.time()
    
    def handle_auto_capture(self):
        """Обработка автоматического захвата"""
        if self.mode == 'auto':
            if time.time() - self.last_capture_time >= AUTO_INTERVAL:
                class_names = list(self.classes_config.keys())
                if class_names:
                    current_class = class_names[self.current_class_index]
                    class_data = self.classes_config[current_class]
                    
                    if class_data['collected'] < class_data['target']:
                        self.capture_image()
                        self.last_capture_time = time.time()
                    else:
                        # Переходим к следующему классу
                        self.next_class()
    
    def run(self):
        """Главный цикл"""
        self.last_capture_time = time.time()
        
        try:
            while self.running:
                try:
                    # Обработка событий
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.running = False
                        
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            if event.button == 1:  # Левая кнопка мыши
                                mouse_pos = pygame.mouse.get_pos()
                                
                                # Проверяем клики по кнопкам
                                if hasattr(self, 'capture_button_rect') and self.capture_button_rect.collidepoint(mouse_pos):
                                    if self.mode == 'manual':
                                        self.capture_image()
                                
                                elif hasattr(self, 'auto_button_rect') and self.auto_button_rect.collidepoint(mouse_pos):
                                    self.mode = 'auto'
                                    self.last_capture_time = time.time()
                                
                                elif hasattr(self, 'manual_button_rect') and self.manual_button_rect.collidepoint(mouse_pos):
                                    self.mode = 'manual'
                                
                                elif hasattr(self, 'next_button_rect') and self.next_button_rect.collidepoint(mouse_pos):
                                    self.next_class()
                                
                                elif hasattr(self, 'prev_button_rect') and self.prev_button_rect.collidepoint(mouse_pos):
                                    self.prev_class()
                                
                                elif hasattr(self, 'quit_button_rect') and self.quit_button_rect.collidepoint(mouse_pos):
                                    self.running = False
                        
                        elif event.type == pygame.KEYDOWN:
                            # Оставляем поддержку клавиатуры для удобства
                            if event.key == pygame.K_q:
                                self.running = False
                            elif event.key == pygame.K_SPACE and self.mode == 'manual':
                                self.capture_image()
                            elif event.key == pygame.K_a:
                                self.mode = 'auto'
                                self.last_capture_time = time.time()
                            elif event.key == pygame.K_m:
                                self.mode = 'manual'
                            elif event.key == pygame.K_n:
                                self.next_class()
                            elif event.key == pygame.K_p:
                                self.prev_class()
                    
                    # Автоматический захват
                    self.handle_auto_capture()
                    
                    # Сбрасываем состояние наведения перед отрисовкой
                    self.hovered_button = None
                    
                    # Отрисовка
                    self.screen.fill(COLOR_BG)
                    self.draw_video()
                    self.draw_panel()
                    
                    pygame.display.flip()
                    self.clock.tick(30)  # 30 FPS
                except Exception as e:
                    print(f"Ошибка в главном цикле: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(0.1)
        except Exception as e:
            print(f"Критическая ошибка в run(): {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Очистка
            try:
                if self.camera:
                    self.camera_running = False
                    time.sleep(0.2)
                    self.camera.release()
            except:
                pass
            try:
                pygame.quit()
            except:
                pass


def main():
    try:
        app = DatasetCollectorGUI()
        app.run()
    except KeyboardInterrupt:
        print("\n⏸️  Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

