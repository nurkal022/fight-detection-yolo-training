#!/usr/bin/env python3
"""
Live инференс pose модели с веб-камеры или видео
Показывает детекции и keypoints в реальном времени
"""

import cv2
import argparse
from pathlib import Path
from ultralytics import YOLO


def run_live_inference(
    model_path: str,
    source: int | str = 0,  # 0 = веб-камера, или путь к видео
    conf: float = 0.5,
    show_fps: bool = True,
    save_video: str = None,
    show_window: bool = True,
):
    """
    Запускает live инференс
    
    Args:
        model_path: Путь к обученной модели (.pt)
        source: 0 для веб-камеры, или путь к видео файлу
        conf: Порог уверенности
        show_fps: Показывать FPS
        save_video: Путь для сохранения видео (опционально)
    """
    print(f"Загрузка модели: {model_path}")
    model = YOLO(model_path)
    
    # Открываем источник видео
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print(f"Ошибка: не удалось открыть источник {source}")
        return
    
    # Получаем параметры видео
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Источник: {source}")
    print(f"Разрешение: {width}x{height}")
    print(f"FPS: {fps}")
    print("\nНажмите 'q' для выхода")
    print("-" * 40)
    
    # Для записи видео
    writer = None
    if save_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(save_video, fourcc, fps, (width, height))
        print(f"Запись в: {save_video}")
    
    # FPS счётчик
    import time
    prev_time = time.time()
    fps_counter = 0
    display_fps = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            # Если видео файл закончился
            if isinstance(source, str):
                print("Видео закончилось")
                break
            continue
        
        # Инференс
        results = model.predict(
            source=frame,
            conf=conf,
            verbose=False,
            show=False,
        )
        
        # Рисуем результаты
        annotated_frame = results[0].plot(
            boxes=True,
            labels=True,
            conf=True,
            kpt_radius=5,
            kpt_line=True,
        )
        
        # FPS
        fps_counter += 1
        current_time = time.time()
        if current_time - prev_time >= 1.0:
            display_fps = fps_counter
            fps_counter = 0
            prev_time = current_time
        
        if show_fps:
            cv2.putText(
                annotated_frame, 
                f"FPS: {display_fps}", 
                (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                (0, 255, 0), 
                2
            )
        
        # Показываем количество детекций
        num_detections = len(results[0].boxes) if results[0].boxes is not None else 0
        cv2.putText(
            annotated_frame,
            f"Detections: {num_detections}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2
        )
        
        # Показываем
        if show_window:
            cv2.imshow("Live Pose Detection", annotated_frame)
        
        # Записываем
        if writer:
            writer.write(annotated_frame)
        
        # Выход по 'q' или автоматически если не показываем
        if show_window:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            # Показываем прогресс
            if fps_counter == 0:
                print(f"  Обработано кадров: {display_fps * (int(current_time - prev_time) + 1)}...", end='\r')
    
    # Освобождаем ресурсы
    cap.release()
    if writer:
        writer.release()
        print(f"\n✓ Видео сохранено: {save_video}")
    if show_window:
        cv2.destroyAllWindows()
    print("Завершено!")


def main():
    parser = argparse.ArgumentParser(description="Live Pose Inference")
    parser.add_argument("--model", type=str, 
                        default="best.pt",
                        help="Путь к модели (.pt)")
    parser.add_argument("--source", type=str, default="0",
                        help="0 для веб-камеры, или путь к видео")
    parser.add_argument("--conf", type=float, default=0.5,
                        help="Порог уверенности (0-1)")
    parser.add_argument("--save", type=str, default=None,
                        help="Путь для сохранения видео")
    parser.add_argument("--no-fps", action="store_true",
                        help="Не показывать FPS")
    parser.add_argument("--no-show", action="store_true",
                        help="Не показывать окно (только сохранять)")
    
    args = parser.parse_args()
    
    # Конвертируем source
    source = int(args.source) if args.source.isdigit() else args.source
    
    # Проверяем модель
    model_path = Path(args.model)
    if not model_path.exists():
        # Пробуем относительный путь
        model_path = Path(__file__).parent / args.model
    
    if not model_path.exists():
        print(f"Ошибка: модель не найдена: {args.model}")
        print("\nДоступные модели:")
        runs_dir = Path(__file__).parent / "runs" / "pose"
        if runs_dir.exists():
            for exp in runs_dir.iterdir():
                weights = exp / "weights" / "best.pt"
                if weights.exists():
                    print(f"  {weights}")
        return
    
    run_live_inference(
        model_path=str(model_path),
        source=source,
        conf=args.conf,
        show_fps=not args.no_fps,
        save_video=args.save,
        show_window=not args.no_show,
    )


if __name__ == "__main__":
    main()

