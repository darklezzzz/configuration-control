# Задание 3. Контроль конфигурации файлов

Модуль core: scan, create_baseline, compare; JSON baseline и дописываемый JSONL-журнал проверок.

## Установка и запуск

Нужны Python 3.11+ и uv. Проект является самостоятельным Git-репозиторием;
его можно скопировать отдельно от учебного workspace. Внутри этого workspace
для команд пакетов используйте `uv run --all-packages <команда>`, либо сначала
из корня выполните `uv sync --all-packages`, затем запускайте команды из `.venv/bin/`.
После отдельного клонирования:

```sh
uv sync --locked
uv run configuration-control --help
uv run pytest -v
uv run ruff check .
```

Все команды ниже выполняются из корня отдельного проекта с новой базой `.data/application.db`.
Команды с идентификатором 1 предполагают пустую базу. Повторная регистрация ID — ошибка.
Вывод — UTF-8 / JSON; неверные аргументы завершаются с кодом 2.

```sh
uv run configuration-control scan src
uv run configuration-control baseline src .data/baselines/BL-001.json BL-001 Reviewer "$(git rev-parse HEAD)"
uv run configuration-control compare src .data/baselines/BL-001.json --history .data/checks.jsonl --report .data/report.json
```

## Архитектура и алгоритм

Каталог → исключения → относительные пути + SHA-256 → утверждённая baseline → повторный снимок → added/removed/changed.

Код в `src/`, автоматизированные проверки в `tests/`, воспроизводимая демонстрация —
`examples/demo.py`, результаты — `examples/`. Запуск: `uv run python examples/demo.py`.
Она использует временное хранилище и обновляет только демонстрационные результаты.

## Связь с управлением конфигурацией

Идентификация, история и проверяемые состояния описаны в [SCMP.md](SCMP.md).
История версий: [CHANGELOG.md](CHANGELOG.md). Учебный отчёт: [REPORT.md](REPORT.md).
Git-доказательства: `git log --graph --oneline --all`, `git branch`, `git tag`.

## Ограничения

Неизменяемость обеспечивается приложением (создание файла в режиме x), а не правами ОС. ID уникальны внутри каталога baseline. Во время сканирования файлы не блокируются; символьные ссылки исключены.
