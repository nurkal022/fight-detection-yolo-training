# Исправление структуры репозитория

## Проблема
Сейчас в репозитории структура:
```
fight-detection-yolo-training/
└── other_version/
    ├── dataset/
    ├── train_yolo.py
    └── ...
```

Нужно чтобы было:
```
fight-detection-yolo-training/
├── dataset/
├── train_yolo.py
└── ...
```

## Решение: Переместить файлы в корень

### Вариант 1: Исправить существующий репозиторий (рекомендуется)

```bash
cd /Users/nurlykhan/fight_detect/third_try/other_version

# 1. Переместить все файлы из other_version в родительскую папку
cd ..
mkdir temp_backup
cp -r other_version/* temp_backup/

# 2. Перейти в репозиторий (если он в другом месте)
# Или создать новый репозиторий прямо в other_version
cd other_version

# 3. Удалить старые коммиты и начать заново
rm -rf .git
git init

# 4. Добавить все файлы
git add .

# 5. Коммит
git commit -m "Initial commit: Fight detection YOLO training project"

# 6. Подключить к репозиторию
git remote add origin https://github.com/nurkal022/fight-detection-yolo-training.git

# 7. Принудительно отправить (перезаписать историю)
git branch -M main
git push -u origin main --force
```

### Вариант 2: Создать новый репозиторий с правильной структурой

```bash
# 1. Создать новую папку для репозитория
cd /Users/nurlykhan/fight_detect/third_try
mkdir fight-detection-yolo-training
cd fight-detection-yolo-training

# 2. Скопировать все из other_version
cp -r ../other_version/* .

# 3. Инициализировать Git
git init

# 4. Добавить все файлы
git add .

# 5. Коммит
git commit -m "Initial commit: Fight detection YOLO training project"

# 6. Подключить к репозиторию
git remote add origin https://github.com/nurkal022/fight-detection-yolo-training.git

# 7. Отправить
git branch -M main
git push -u origin main --force
```

### Вариант 3: Использовать git subtree или filter-branch (сложнее)

Этот вариант сохраняет историю, но более сложный.

## Рекомендация

Используйте **Вариант 2** - он самый простой и чистый.

