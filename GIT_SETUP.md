# Инструкция по загрузке проекта в Git

## Шаг 1: Инициализация Git репозитория

```bash
cd /Users/nurlykhan/fight_detect/third_try/other_version

# Инициализировать Git (если еще не инициализирован)
git init

# Проверить статус
git status
```

## Шаг 2: Добавление файлов

```bash
# Добавить все файлы (кроме тех, что в .gitignore)
git add .

# Проверить что будет добавлено
git status
```

## Шаг 3: Первый коммит

```bash
git commit -m "Initial commit: Fight detection YOLO training project with dataset"
```

## Шаг 4: Создание репозитория на GitHub/GitLab

1. Создайте новый репозиторий на GitHub/GitLab
2. **НЕ** добавляйте README, .gitignore или лицензию (они уже есть)

## Шаг 5: Подключение к удаленному репозиторию

```bash
# Добавить remote (замените URL на ваш)
git remote add origin https://github.com/ваш_username/ваш_repo.git

# Или через SSH:
# git remote add origin git@github.com:ваш_username/ваш_repo.git

# Проверить remote
git remote -v
```

## Шаг 6: Отправка в репозиторий

```bash
# Отправить код
git push -u origin main

# Если ветка называется master:
# git push -u origin master
```

## Важные замечания

### Размер датасета

Датасет может быть большим. Проверьте размер:

```bash
du -sh dataset/
```

Если датасет очень большой (>100MB), рассмотрите:
1. Использование Git LFS (Large File Storage)
2. Загрузку датасета отдельно (Google Drive, Dropbox, etc.)

### Git LFS для больших файлов (опционально)

```bash
# Установить Git LFS
git lfs install

# Отслеживать изображения
git lfs track "dataset/**/*.jpg"
git lfs track "dataset/**/*.png"
git lfs track "yolo_dataset/**/*.jpg"

# Добавить .gitattributes
git add .gitattributes
git commit -m "Add Git LFS tracking for images"
```

### Что НЕ будет загружено (благодаря .gitignore)

- Результаты обучения (`fight_detection/`)
- Кэши (`*.cache`)
- Модели (`*.pt`)
- Виртуальные окружения (`venv/`)
- Логи (`*.log`)

### Что БУДЕТ загружено

- ✅ Весь код проекта
- ✅ Датасет с изображениями и метками
- ✅ Конфигурационные файлы
- ✅ Скрипты обучения
- ✅ Requirements.txt
- ✅ Инструкции

## Проверка перед отправкой

```bash
# Проверить размер репозитория
du -sh .git/

# Проверить что будет отправлено
git ls-files | wc -l

# Посмотреть список файлов
git ls-files
```

## После клонирования на другом компьютере

См. файл `SETUP.md` для инструкций по установке и запуску.

