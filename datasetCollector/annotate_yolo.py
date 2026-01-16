#!/usr/bin/env python3
"""
YOLO Annotation Tool
Инструмент для разметки bounding boxes в формате YOLO

Использование:
    python annotate_yolo.py
    
Управление:
    Мышь - рисование bbox (зажать и тянуть)
    N / Right Arrow - следующее изображение
    P / Left Arrow - предыдущее изображение
    D / Delete - удалить выбранный bbox
    C - выбрать класс для следующего bbox
    S / Ctrl+S - сохранить аннотации
    Z / Ctrl+Z - отменить последний bbox
    Q / Escape - выход
"""

import pygame
import cv2
import json
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Директория скрипта
SCRIPT_DIR = Path(__file__).parent.absolute()

# Конфигурация
DATASET_DIR = SCRIPT_DIR / 'dataset'
CLASSES_FILE = SCRIPT_DIR / 'dataset_classes.json'
ANNOTATIONS_DIR = SCRIPT_DIR / 'annotations'

# Размеры окна
MIN_WINDOW_WIDTH = 1024
MIN_WINDOW_HEIGHT = 600
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800

# Цвета (различные для разных классов)
COLORS = [
    (255, 87, 87),    # Красный
    (87, 255, 87),    # Зеленый
    (87, 87, 255),    # Синий
    (255, 255, 87),   # Желтый
    (255, 87, 255),   # Пурпурный
    (87, 255, 255),   # Голубой
    (255, 165, 87),   # Оранжевый
    (165, 87, 255),   # Фиолетовый
    (87, 255, 165),   # Бирюзовый
    (255, 87, 165),   # Розовый
]

COLOR_BG = (25, 25, 30)
COLOR_PANEL = (35, 35, 40)
COLOR_TEXT = (240, 240, 240)
COLOR_PRIMARY = (66, 165, 245)
COLOR_SUCCESS = (102, 187, 106)
COLOR_WARNING = (255, 167, 38)
COLOR_ERROR = (239, 83, 80)
COLOR_HOVER = (80, 80, 90)


class BoundingBox:
    """Класс для хранения bounding box"""
    def __init__(self, x1: float, y1: float, x2: float, y2: float, class_id: int):
        self.x1 = min(x1, x2)
        self.y1 = min(y1, y2)
        self.x2 = max(x1, x2)
        self.y2 = max(y1, y2)
        self.class_id = class_id
    
    def to_yolo(self, img_width: int, img_height: int) -> Tuple[int, float, float, float, float]:
        """Конвертировать в формат YOLO: class_id, center_x, center_y, width, height (все нормализованы)"""
        center_x = ((self.x1 + self.x2) / 2) / img_width
        center_y = ((self.y1 + self.y2) / 2) / img_height
        width = (self.x2 - self.x1) / img_width
        height = (self.y2 - self.y1) / img_height
        return self.class_id, center_x, center_y, width, height
    
    @staticmethod
    def from_yolo(class_id: int, cx: float, cy: float, w: float, h: float, 
                  img_width: int, img_height: int) -> 'BoundingBox':
        """Создать из формата YOLO"""
        x1 = (cx - w/2) * img_width
        y1 = (cy - h/2) * img_height
        x2 = (cx + w/2) * img_width
        y2 = (cy + h/2) * img_height
        return BoundingBox(x1, y1, x2, y2, class_id)
    
    def contains_point(self, x: float, y: float) -> bool:
        """Проверить, содержит ли bbox точку"""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2


class YOLOAnnotator:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("YOLO Annotation Tool")
        self.clock = pygame.time.Clock()
        
        # Шрифты
        self.font_large = pygame.font.Font(None, 42)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 22)
        
        # Размеры окна
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        self.panel_width = 320
        self.image_area_width = self.window_width - self.panel_width
        self.image_area_height = self.window_height
        
        # Классы и изображения
        self.classes = []
        self.class_names = []
        self.images = []
        self.current_image_index = 0
        self.current_image = None
        self.current_image_surface = None
        self.original_image_size = (0, 0)
        
        # Масштабирование изображения
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Аннотации
        self.bboxes: List[BoundingBox] = []
        self.selected_bbox_index = -1
        self.current_class_id = 0
        self.unsaved_changes = False
        
        # Рисование нового bbox
        self.drawing = False
        self.draw_start = None
        self.draw_end = None
        
        # UI состояние
        self.running = True
        self.show_class_selector = False
        self.hovered_class = -1
        self.status_message = ""
        self.status_time = 0
        
        # Загрузка конфигурации
        self.load_classes()
        self.scan_images()
        
        if self.images:
            self.load_image(0)
    
    def load_classes(self):
        """Загрузить классы из конфигурации"""
        if not CLASSES_FILE.exists():
            print(f"❌ Файл {CLASSES_FILE} не найден!")
            sys.exit(1)
        
        try:
            with open(CLASSES_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.classes = config.get('classes', [])
            self.class_names = [cls['name'] for cls in self.classes]
            print(f"✅ Загружено {len(self.class_names)} классов")
        except Exception as e:
            print(f"❌ Ошибка загрузки классов: {e}")
            sys.exit(1)
    
    def scan_images(self):
        """Сканировать все изображения в датасете"""
        self.images = []
        
        if not DATASET_DIR.exists():
            print(f"⚠️  Директория {DATASET_DIR} не найдена")
            return
        
        # Сканируем все подпапки
        for class_dir in sorted(DATASET_DIR.iterdir()):
            if class_dir.is_dir():
                for img_path in sorted(class_dir.glob('*.jpg')):
                    self.images.append(img_path)
                for img_path in sorted(class_dir.glob('*.jpeg')):
                    self.images.append(img_path)
                for img_path in sorted(class_dir.glob('*.png')):
                    self.images.append(img_path)
        
        print(f"✅ Найдено {len(self.images)} изображений")
    
    def load_image(self, index: int):
        """Загрузить изображение по индексу"""
        if not self.images or index < 0 or index >= len(self.images):
            return
        
        # Сохраняем текущие аннотации если есть несохраненные изменения
        if self.unsaved_changes and self.current_image is not None:
            self.save_annotations()
        
        self.current_image_index = index
        img_path = self.images[index]
        
        # Загружаем изображение через OpenCV
        img = cv2.imread(str(img_path))
        if img is None:
            self.set_status(f"Ошибка загрузки: {img_path.name}", COLOR_ERROR)
            return
        
        # Конвертируем BGR -> RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.current_image = img_rgb
        self.original_image_size = (img_rgb.shape[1], img_rgb.shape[0])
        
        # Вычисляем масштаб для отображения
        self.calculate_scale()
        
        # Создаем pygame surface
        self.update_image_surface()
        
        # Загружаем существующие аннотации
        self.load_annotations()
        
        self.set_status(f"Загружено: {img_path.name}", COLOR_SUCCESS)
    
    def calculate_scale(self):
        """Вычислить масштаб для отображения изображения"""
        if self.current_image is None:
            return
        
        img_w, img_h = self.original_image_size
        area_w = self.image_area_width - 40
        area_h = self.image_area_height - 40
        
        scale_w = area_w / img_w
        scale_h = area_h / img_h
        self.scale = min(scale_w, scale_h)
        
        # Центрируем изображение
        scaled_w = int(img_w * self.scale)
        scaled_h = int(img_h * self.scale)
        self.offset_x = (self.image_area_width - scaled_w) // 2
        self.offset_y = (self.image_area_height - scaled_h) // 2
    
    def update_image_surface(self):
        """Обновить pygame surface изображения"""
        if self.current_image is None:
            return
        
        img_w, img_h = self.original_image_size
        scaled_w = int(img_w * self.scale)
        scaled_h = int(img_h * self.scale)
        
        # Масштабируем изображение
        scaled_img = cv2.resize(self.current_image, (scaled_w, scaled_h), interpolation=cv2.INTER_LINEAR)
        
        # Создаем pygame surface
        self.current_image_surface = pygame.surfarray.make_surface(scaled_img.swapaxes(0, 1))
    
    def get_annotation_path(self) -> Path:
        """Получить путь к файлу аннотаций для текущего изображения"""
        if not self.images or self.current_image_index >= len(self.images):
            return None
        
        img_path = self.images[self.current_image_index]
        
        # Создаем структуру папок в annotations
        relative_path = img_path.relative_to(DATASET_DIR)
        annotation_path = ANNOTATIONS_DIR / relative_path.parent / (img_path.stem + '.txt')
        
        return annotation_path
    
    def load_annotations(self):
        """Загрузить существующие аннотации"""
        self.bboxes = []
        self.selected_bbox_index = -1
        
        ann_path = self.get_annotation_path()
        if ann_path is None or not ann_path.exists():
            self.unsaved_changes = False
            return
        
        try:
            with open(ann_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        class_id = int(parts[0])
                        cx, cy, w, h = map(float, parts[1:])
                        
                        bbox = BoundingBox.from_yolo(
                            class_id, cx, cy, w, h,
                            self.original_image_size[0],
                            self.original_image_size[1]
                        )
                        self.bboxes.append(bbox)
            
            self.unsaved_changes = False
        except Exception as e:
            self.set_status(f"Ошибка загрузки аннотаций: {e}", COLOR_ERROR)
    
    def save_annotations(self):
        """Сохранить аннотации в формате YOLO"""
        ann_path = self.get_annotation_path()
        if ann_path is None:
            return
        
        # Создаем директорию если нужно
        ann_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(ann_path, 'w') as f:
                for bbox in self.bboxes:
                    yolo_data = bbox.to_yolo(
                        self.original_image_size[0],
                        self.original_image_size[1]
                    )
                    f.write(f"{yolo_data[0]} {yolo_data[1]:.6f} {yolo_data[2]:.6f} {yolo_data[3]:.6f} {yolo_data[4]:.6f}\n")
            
            self.unsaved_changes = False
            self.set_status("Сохранено!", COLOR_SUCCESS)
        except Exception as e:
            self.set_status(f"Ошибка сохранения: {e}", COLOR_ERROR)
    
    def screen_to_image(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """Конвертировать экранные координаты в координаты изображения"""
        img_x = (screen_x - self.offset_x) / self.scale
        img_y = (screen_y - self.offset_y) / self.scale
        return img_x, img_y
    
    def image_to_screen(self, img_x: float, img_y: float) -> Tuple[int, int]:
        """Конвертировать координаты изображения в экранные"""
        screen_x = int(img_x * self.scale + self.offset_x)
        screen_y = int(img_y * self.scale + self.offset_y)
        return screen_x, screen_y
    
    def is_in_image_area(self, x: int, y: int) -> bool:
        """Проверить, находится ли точка в области изображения"""
        return x < self.image_area_width
    
    def handle_resize(self, new_width: int, new_height: int):
        """Обработать изменение размера окна"""
        self.window_width = max(MIN_WINDOW_WIDTH, new_width)
        self.window_height = max(MIN_WINDOW_HEIGHT, new_height)
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        
        self.panel_width = max(280, min(400, int(self.window_width * 0.23)))
        self.image_area_width = self.window_width - self.panel_width
        self.image_area_height = self.window_height
        
        self.calculate_scale()
        self.update_image_surface()
    
    def set_status(self, message: str, color=COLOR_TEXT):
        """Установить статусное сообщение"""
        self.status_message = message
        self.status_color = color
        self.status_time = pygame.time.get_ticks()
    
    def draw_text(self, text: str, pos: Tuple[int, int], font, color=COLOR_TEXT, center=False) -> int:
        """Отрисовать текст"""
        text_surface = font.render(str(text), True, color)
        if center:
            pos = (pos[0] - text_surface.get_width() // 2, pos[1])
        self.screen.blit(text_surface, pos)
        return text_surface.get_height()
    
    def draw_button(self, pos: Tuple[int, int], size: Tuple[int, int], text: str, 
                    color, enabled=True, selected=False) -> pygame.Rect:
        """Отрисовать кнопку"""
        x, y = pos
        width, height = size
        
        button_rect = pygame.Rect(x, y, width, height)
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = button_rect.collidepoint(mouse_pos) and enabled
        
        if enabled:
            if selected:
                draw_color = tuple(min(255, c + 50) for c in color)
            elif is_hovered:
                draw_color = tuple(min(255, c + 30) for c in color)
            else:
                draw_color = color
            
            pygame.draw.rect(self.screen, draw_color, button_rect)
            pygame.draw.rect(self.screen, (200, 200, 200) if is_hovered else (120, 120, 120), button_rect, 2)
        else:
            pygame.draw.rect(self.screen, (50, 50, 50), button_rect)
            pygame.draw.rect(self.screen, (80, 80, 80), button_rect, 1)
        
        text_surface = self.font_small.render(text, True, COLOR_TEXT if enabled else (100, 100, 100))
        text_x = x + (width - text_surface.get_width()) // 2
        text_y = y + (height - text_surface.get_height()) // 2
        self.screen.blit(text_surface, (text_x, text_y))
        
        return button_rect
    
    def draw_image_area(self):
        """Отрисовать область изображения"""
        # Фон
        pygame.draw.rect(self.screen, COLOR_BG, (0, 0, self.image_area_width, self.image_area_height))
        
        if self.current_image_surface is None:
            self.draw_text("Нет изображений", (self.image_area_width // 2, self.image_area_height // 2),
                          self.font_large, (100, 100, 100), center=True)
            return
        
        # Изображение
        self.screen.blit(self.current_image_surface, (self.offset_x, self.offset_y))
        
        # Рисуем существующие bbox'ы
        for i, bbox in enumerate(self.bboxes):
            color = COLORS[bbox.class_id % len(COLORS)]
            
            # Конвертируем координаты
            x1, y1 = self.image_to_screen(bbox.x1, bbox.y1)
            x2, y2 = self.image_to_screen(bbox.x2, bbox.y2)
            
            # Рисуем прямоугольник
            thickness = 3 if i == self.selected_bbox_index else 2
            pygame.draw.rect(self.screen, color, (x1, y1, x2 - x1, y2 - y1), thickness)
            
            # Метка класса
            class_name = self.class_names[bbox.class_id] if bbox.class_id < len(self.class_names) else f"cls_{bbox.class_id}"
            label = self.font_small.render(class_name, True, COLOR_TEXT)
            label_bg = pygame.Rect(x1, y1 - 22, label.get_width() + 6, 20)
            pygame.draw.rect(self.screen, color, label_bg)
            self.screen.blit(label, (x1 + 3, y1 - 20))
            
            # Подсветка выбранного
            if i == self.selected_bbox_index:
                pygame.draw.rect(self.screen, (255, 255, 255), (x1 - 2, y1 - 2, x2 - x1 + 4, y2 - y1 + 4), 1)
        
        # Рисуем текущий bbox в процессе создания
        if self.drawing and self.draw_start and self.draw_end:
            color = COLORS[self.current_class_id % len(COLORS)]
            x1 = min(self.draw_start[0], self.draw_end[0])
            y1 = min(self.draw_start[1], self.draw_end[1])
            x2 = max(self.draw_start[0], self.draw_end[0])
            y2 = max(self.draw_start[1], self.draw_end[1])
            
            pygame.draw.rect(self.screen, color, (x1, y1, x2 - x1, y2 - y1), 2)
            
            # Размеры bbox
            img_x1, img_y1 = self.screen_to_image(x1, y1)
            img_x2, img_y2 = self.screen_to_image(x2, y2)
            size_text = f"{int(img_x2 - img_x1)}x{int(img_y2 - img_y1)}"
            self.draw_text(size_text, (x2 + 5, y2 + 5), self.font_small, color)
    
    def draw_panel(self):
        """Отрисовать боковую панель"""
        panel_x = self.image_area_width
        panel_rect = pygame.Rect(panel_x, 0, self.panel_width, self.window_height)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect)
        
        y = 20
        
        # Заголовок
        self.draw_text("YOLO Annotator", (panel_x + self.panel_width // 2, y), 
                      self.font_large, COLOR_PRIMARY, center=True)
        y += 50
        
        # Информация о файле
        if self.images:
            img_path = self.images[self.current_image_index]
            self.draw_text(f"Файл: {img_path.name[:20]}...", (panel_x + 15, y), self.font_small)
            y += 25
            self.draw_text(f"Изображение: {self.current_image_index + 1}/{len(self.images)}", 
                          (panel_x + 15, y), self.font_small, COLOR_TEXT)
            y += 25
            if self.original_image_size[0] > 0:
                self.draw_text(f"Размер: {self.original_image_size[0]}x{self.original_image_size[1]}", 
                              (panel_x + 15, y), self.font_small)
            y += 35
        
        # Текущий класс
        self.draw_text("Текущий класс:", (panel_x + 15, y), self.font_medium)
        y += 30
        
        class_color = COLORS[self.current_class_id % len(COLORS)]
        class_name = self.class_names[self.current_class_id] if self.current_class_id < len(self.class_names) else "?"
        pygame.draw.rect(self.screen, class_color, (panel_x + 15, y, 20, 20))
        self.draw_text(class_name, (panel_x + 45, y), self.font_medium, class_color)
        y += 35
        
        # Выбор класса
        self.draw_text("Выбор класса (C):", (panel_x + 15, y), self.font_small, (180, 180, 180))
        y += 25
        
        self.class_buttons = []
        btn_width = (self.panel_width - 50) // 2
        btn_height = 28
        
        for i, cls_name in enumerate(self.class_names):
            col = i % 2
            row = i // 2
            btn_x = panel_x + 15 + col * (btn_width + 10)
            btn_y = y + row * (btn_height + 5)
            
            color = COLORS[i % len(COLORS)]
            darker_color = tuple(max(0, c - 80) for c in color)
            
            btn = self.draw_button(
                (btn_x, btn_y), 
                (btn_width, btn_height),
                cls_name[:12], 
                darker_color,
                True,
                i == self.current_class_id
            )
            self.class_buttons.append((btn, i))
        
        y += ((len(self.class_names) + 1) // 2) * (btn_height + 5) + 20
        
        # Bbox список
        self.draw_text(f"Bounding Boxes ({len(self.bboxes)}):", (panel_x + 15, y), self.font_medium)
        y += 30
        
        self.bbox_buttons = []
        for i, bbox in enumerate(self.bboxes[:8]):  # Показываем максимум 8
            color = COLORS[bbox.class_id % len(COLORS)]
            class_name = self.class_names[bbox.class_id] if bbox.class_id < len(self.class_names) else f"cls_{bbox.class_id}"
            
            btn_rect = pygame.Rect(panel_x + 15, y, self.panel_width - 30, 25)
            is_selected = i == self.selected_bbox_index
            
            bg_color = (60, 60, 70) if is_selected else (45, 45, 50)
            pygame.draw.rect(self.screen, bg_color, btn_rect)
            pygame.draw.rect(self.screen, color, (panel_x + 15, y, 5, 25))
            
            text = f"{i+1}. {class_name}"
            self.draw_text(text, (panel_x + 25, y + 3), self.font_small)
            
            self.bbox_buttons.append((btn_rect, i))
            y += 28
        
        if len(self.bboxes) > 8:
            self.draw_text(f"... и ещё {len(self.bboxes) - 8}", (panel_x + 15, y), 
                          self.font_small, (120, 120, 120))
            y += 25
        
        # Кнопки навигации - внизу
        y = self.window_height - 180
        
        self.draw_text("Управление:", (panel_x + 15, y), self.font_medium)
        y += 35
        
        btn_w = (self.panel_width - 50) // 2
        
        self.prev_btn = self.draw_button(
            (panel_x + 15, y), (btn_w, 35),
            "← Prev (P)", (70, 100, 140), len(self.images) > 1
        )
        self.next_btn = self.draw_button(
            (panel_x + 25 + btn_w, y), (btn_w, 35),
            "Next (N) →", (70, 100, 140), len(self.images) > 1
        )
        y += 45
        
        self.save_btn = self.draw_button(
            (panel_x + 15, y), (self.panel_width - 30, 35),
            "💾 Сохранить (S)", COLOR_SUCCESS if self.unsaved_changes else (60, 90, 60),
            True
        )
        y += 45
        
        self.delete_btn = self.draw_button(
            (panel_x + 15, y), (self.panel_width - 30, 35),
            "🗑 Удалить bbox (D)", COLOR_ERROR if self.selected_bbox_index >= 0 else (90, 60, 60),
            self.selected_bbox_index >= 0
        )
        
        # Статус
        if self.status_message and pygame.time.get_ticks() - self.status_time < 3000:
            y = self.window_height - 30
            self.draw_text(self.status_message, (panel_x + self.panel_width // 2, y), 
                          self.font_small, self.status_color, center=True)
        
        # Индикатор несохраненных изменений
        if self.unsaved_changes:
            pygame.draw.circle(self.screen, COLOR_WARNING, (panel_x + self.panel_width - 20, 25), 8)
    
    def handle_mouse_down(self, pos: Tuple[int, int], button: int):
        """Обработка нажатия мыши"""
        if button != 1:  # Только левая кнопка
            return
        
        x, y = pos
        
        # Клик в области изображения
        if self.is_in_image_area(x, y) and self.current_image is not None:
            # Проверяем клик по существующему bbox
            img_x, img_y = self.screen_to_image(x, y)
            
            clicked_bbox = -1
            for i, bbox in enumerate(self.bboxes):
                if bbox.contains_point(img_x, img_y):
                    clicked_bbox = i
            
            if clicked_bbox >= 0:
                self.selected_bbox_index = clicked_bbox
            else:
                # Начинаем рисовать новый bbox
                self.selected_bbox_index = -1
                self.drawing = True
                self.draw_start = pos
                self.draw_end = pos
        
        # Клик по кнопкам классов
        for btn_rect, class_id in self.class_buttons:
            if btn_rect.collidepoint(pos):
                self.current_class_id = class_id
                return
        
        # Клик по кнопкам bbox
        for btn_rect, bbox_id in self.bbox_buttons:
            if btn_rect.collidepoint(pos):
                self.selected_bbox_index = bbox_id
                return
        
        # Кнопки навигации
        if hasattr(self, 'prev_btn') and self.prev_btn.collidepoint(pos):
            self.navigate(-1)
        elif hasattr(self, 'next_btn') and self.next_btn.collidepoint(pos):
            self.navigate(1)
        elif hasattr(self, 'save_btn') and self.save_btn.collidepoint(pos):
            self.save_annotations()
        elif hasattr(self, 'delete_btn') and self.delete_btn.collidepoint(pos):
            self.delete_selected_bbox()
    
    def handle_mouse_up(self, pos: Tuple[int, int], button: int):
        """Обработка отпускания мыши"""
        if button != 1:
            return
        
        if self.drawing and self.draw_start:
            self.draw_end = pos
            
            # Конвертируем координаты
            img_x1, img_y1 = self.screen_to_image(self.draw_start[0], self.draw_start[1])
            img_x2, img_y2 = self.screen_to_image(self.draw_end[0], self.draw_end[1])
            
            # Проверяем минимальный размер bbox
            width = abs(img_x2 - img_x1)
            height = abs(img_y2 - img_y1)
            
            if width > 10 and height > 10:
                # Ограничиваем координаты размером изображения
                img_x1 = max(0, min(img_x1, self.original_image_size[0]))
                img_y1 = max(0, min(img_y1, self.original_image_size[1]))
                img_x2 = max(0, min(img_x2, self.original_image_size[0]))
                img_y2 = max(0, min(img_y2, self.original_image_size[1]))
                
                bbox = BoundingBox(img_x1, img_y1, img_x2, img_y2, self.current_class_id)
                self.bboxes.append(bbox)
                self.selected_bbox_index = len(self.bboxes) - 1
                self.unsaved_changes = True
                self.set_status(f"Добавлен bbox: {self.class_names[self.current_class_id]}", COLOR_SUCCESS)
        
        self.drawing = False
        self.draw_start = None
        self.draw_end = None
    
    def handle_mouse_move(self, pos: Tuple[int, int]):
        """Обработка движения мыши"""
        if self.drawing:
            self.draw_end = pos
    
    def navigate(self, direction: int):
        """Навигация между изображениями"""
        if not self.images:
            return
        
        new_index = (self.current_image_index + direction) % len(self.images)
        self.load_image(new_index)
    
    def delete_selected_bbox(self):
        """Удалить выбранный bbox"""
        if self.selected_bbox_index >= 0 and self.selected_bbox_index < len(self.bboxes):
            del self.bboxes[self.selected_bbox_index]
            self.selected_bbox_index = -1
            self.unsaved_changes = True
            self.set_status("Bbox удален", COLOR_WARNING)
    
    def undo_last_bbox(self):
        """Отменить последний bbox"""
        if self.bboxes:
            self.bboxes.pop()
            self.selected_bbox_index = -1
            self.unsaved_changes = True
            self.set_status("Отмена", COLOR_WARNING)
    
    def run(self):
        """Главный цикл"""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.unsaved_changes:
                        self.save_annotations()
                    self.running = False
                
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event.w, event.h)
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_down(event.pos, event.button)
                
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event.pos, event.button)
                
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_move(event.pos)
                
                elif event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        if self.unsaved_changes:
                            self.save_annotations()
                        self.running = False
                    
                    elif event.key == pygame.K_n or event.key == pygame.K_RIGHT:
                        self.navigate(1)
                    
                    elif event.key == pygame.K_p or event.key == pygame.K_LEFT:
                        self.navigate(-1)
                    
                    elif event.key == pygame.K_s:
                        self.save_annotations()
                    
                    elif event.key == pygame.K_d or event.key == pygame.K_DELETE:
                        self.delete_selected_bbox()
                    
                    elif event.key == pygame.K_z:
                        self.undo_last_bbox()
                    
                    elif event.key == pygame.K_c:
                        # Переключить класс
                        self.current_class_id = (self.current_class_id + 1) % len(self.class_names)
                    
                    # Цифры 1-9 для быстрого выбора класса
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        class_id = event.key - pygame.K_1
                        if class_id < len(self.class_names):
                            self.current_class_id = class_id
            
            # Отрисовка
            self.screen.fill(COLOR_BG)
            self.draw_image_area()
            self.draw_panel()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()


def main():
    print("=" * 50)
    print("YOLO Annotation Tool")
    print("=" * 50)
    
    # Создаем директорию для аннотаций
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        app = YOLOAnnotator()
        app.run()
    except KeyboardInterrupt:
        print("\n⏸️  Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
