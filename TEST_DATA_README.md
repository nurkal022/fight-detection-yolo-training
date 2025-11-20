# Тестовые данные для демонстрации

Этот скрипт добавляет тестовые данные в систему детекции для демонстрации функционала.

## Использование

### Базовое использование (создает все данные)

```bash
python add_test_data.py
```

### Опции

```bash
# Создать только камеры
python add_test_data.py --cameras-only

# Создать только события
python add_test_data.py --events-only

# Создать только логи
python add_test_data.py --logs-only

# Создать камеры и события (без логов)
python add_test_data.py --no-logs

# Создать камеры и логи (без событий)
python add_test_data.py --no-events
```

## Что создается

### 📹 Тестовые камеры (6 штук)

1. **Главный вход - Вестибюль** (webcam 0)
   - Локация: Вестибюль, 1 этаж
   - Порог уверенности: 0.65

2. **Камера 2 - Коридор** (webcam 1)
   - Локация: Коридор, 2 этаж
   - Порог уверенности: 0.6

3. **Демо RTSP камера**
   - Источник: Демо RTSP поток (ipvmdemo.dyndns.org)
   - Локация: Демо локация
   - Порог уверенности: 0.7

4. **Тестовая камера - Офис** (webcam 2)
   - Локация: Офис, 3 этаж
   - Порог уверенности: 0.55

5. **Фейк камера - Склад** (webcam 3)
   - Локация: Склад, подвал
   - Порог уверенности: 0.65

6. **Демо файл камера**
   - Источник: test_video.mp4 (файл)
   - Локация: Тестовая локация
   - Порог уверенности: 0.6

### 🔴 Тестовые события детекции

- 2-5 событий на каждую камеру
- Случайные классы детекции (covering_face, neck_grab, face_slap и т.д.)
- Случайные временные метки за последние 7 дней
- Разные статусы (active, resolved, false_positive)

### 📝 Системные логи

- 20 тестовых логов
- Разные уровни (INFO, WARNING, ERROR)
- Случайные временные метки за последние 3 дня

## Примечания

- Скрипт не перезаписывает существующие камеры (проверяет по имени)
- Все камеры создаются с `is_active=False` (не запущены автоматически)
- Для запуска детекции используйте веб-интерфейс или API

## Демо RTSP потоки

Для тестирования RTSP камер можно использовать публичные демо потоки:

- `rtsp://demo:demo@ipvmdemo.dyndns.org:5541/onvif-media/media.amp?profile=profile_1_h264&sessiontimeout=60&streamtimeout=60`
- `rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4`

## Очистка тестовых данных

Для удаления всех тестовых данных:

```python
from app import create_app, db
from app.models import Camera, DetectionEvent, SystemLog

app = create_app()
with app.app_context():
    # Удалить все камеры с "Тест" или "Демо" в названии
    Camera.query.filter(
        (Camera.name.like('%Тест%')) | 
        (Camera.name.like('%Демо%')) |
        (Camera.name.like('%Фейк%'))
    ).delete()
    
    # Или удалить все события
    DetectionEvent.query.delete()
    
    # Или удалить все логи
    SystemLog.query.delete()
    
    db.session.commit()
```

