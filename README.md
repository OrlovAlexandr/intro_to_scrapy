# Знакомство с Scrapy

## Описание
Этот проект представляет собой веб-скрапер для сбора информации о фильмах с русскоязычной Википедии. Скрапер находит фильмы в алфавитном порядке, переходит на их страницы и извлекает ключевую информацию, включая:

- **Название**
- **Оригинальное название**
- **Жанр**
- **Режиссёр**
- **Страна**
- **Год выпуска**
- **Рейтинг IMDb** (если доступен)

Данные сохраняются в CSV-файл (`movies.csv`).

## Требования
Для работы скрапера необходимо установить следующие зависимости:

```bash
pip install scrapy beautifulsoup4 pandas requests lxml
```

## Запуск проекта

1. Убедитесь, что у вас установлен **Python 3.x** и необходимые библиотеки.
2. Запустите скрапер командой:

```bash
scrapy crawl movies
```

По завершении работы скрапера все собранные данные будут сохранены в `movies.csv`.

## Структура проекта

```
intro_to_scrapy/
│── movies_parser/             # Основная директория Scrapy-проекта
│   ├── movies_parser/         
│   │   ├── spiders/           # Каталог со скраперами
│   │   │   ├── movies.py      # Основной скрапер для сбора данных о фильмах
│   │   ├── items.py           # Определение структуры данных (Item)
│   │   ├── middlewares.py     # Промежуточные обработки запросов и ответов
│   │   ├── pipelines.py       # Логика обработки и сохранения данных
│   │   ├── settings.py        # Файл конфигурации Scrapy
│   │── scrapy.cfg             # Глобальный конфигурационный файл Scrapy
│── README.md                  # Документация проекта
│── requirements.txt           # Список зависимостей для установки
```

## Как работает скрапер

1. **Начальная страница**: `https://ru.wikipedia.org/wiki/Категория:Фильмы_по_алфавиту`.
2. **Сбор ссылок**: скрапер ищет ссылки на страницы фильмов.
3. **Пагинация**: если есть следующая страница, скрапер переходит на неё.
4. **Сбор данных**: на странице фильма извлекается информация из инфобокса.
5. **Рейтинг IMDb**: выполняется поиск рейтинга на IMDb.
6. **Сохранение данных**: информация записывается в `movies.csv`.

## Возможные проблемы

- IMDb может изменить структуру страниц, из-за чего может перестать работать сбор рейтингов.
- Некоторые фильмы могут не содержать полных данных, что приведёт к появлению пропущенных значений в CSV.
- Wikipedia и IMDb могут заблокировать частые запросы — необходимо использовать прокси или уменьшить скорость запросов. Для этого рекомендуется установить `scrapy_proxies`:

```bash
pip install scrapy_proxies
```

В файле настроек `settings.py` необходимо указать путь к файлу со списком прокси-серверов:

**settings.py**
```python
PROXY_LIST = '/path/to/proxy/list.txt'
```

После работы скрапера данные сохраняются в `movies.csv` в следующем формате:

| title                      | original_title                | genre                       | director                                            | country                            | year | imdb_rating |
|----------------------------|-------------------------------|-----------------------------|-----------------------------------------------------|------------------------------------|------|-------------|
| ? (фильм)                  | ?                             | драматический фильм         | Ханун Брамантио                                     | Индонезия                          | 2011 | 7.0         |
| 4 маленькие девочки        | 4 Little Girls                | Исторический документальный | Спайк Ли                                            | США                                | 1997 | 7.8         |
| 4 x 4 (фильм)              | 4 x 4                         | драма, комедия              | Рольф Клеменс, Паппе Кёрлунг-Шмидт, Мауну Куркваара | Финляндия, Норвегия, Швеция, Дания | 1965 | 6.9         |
| 4 месяца, 3 недели и 2 дня | 4 luni, 3 săptămâni și 2 zile | драма                       | Кристиан Мунджиу                                    | Румыния                            | 2007 | 7.9         |
| 5 недель (фильм)           | 5 недель                      | трагикомедия                | Александр Андреев                                   | Россия                             | 2021 | 4.7         |