import re
from typing import Any
from typing import ClassVar

import pandas as pd
import requests
import scrapy
from bs4 import BeautifulSoup
from scrapy import Request


def clean_text(text):
    """Удаляет сноски и лишние пробелы."""
    text = re.sub(r"\[\d+\]|\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_refs(lst):
    """Удаляет ссылки из списка."""
    return [s for s in lst
            if not (s.startswith('[') and s.endswith(']'))]


def get_infobox_value(label, infobox):
    """Функция для извлечения одиночных значений из инфобокса."""
    if not infobox:
        return None
    row = infobox.find("th", string=re.compile(label))
    if row:
        value = row.find_next_sibling("td")
        if value:
            return clean_text(value.text)
    return None


def get_infobox_imdb_link(infobox):
    """Функция для извлечения ссылки на IMDB из инфобокса."""
    if not infobox:
        return None
    row = infobox.find("th", string=re.compile("IMDb"))
    if row:
        value = row.find_next_sibling("td")
        if value:
            return value.find("a").get("href")
    return None


def get_list_from_infobox(label, infobox):
    """Функция для извлечения списка значений из инфобокса."""
    if not infobox:
        return []
    row = infobox.find("th", string=re.compile(label))
    if not row:
        return []

    td = row.find_next_sibling("td")
    if not td:
        return []

    # Пытаемся извлечь ссылки
    items = [a.text for a in td.find_all("a") if a.text.strip()]
    if not items:
        # Пытаемся извлечь списки, если строки разделены тегом </br> то преобразуем в список
        items = [", ".join(s.stripped_strings) for s in td.find_all("span") if s.text.strip()]

    # Удаляем ссылки
    return remove_refs(items)


def get_original_title(infobox):
    """Извлекает оригинальное название фильма, если оно есть."""
    if not infobox:
        return None

    rows = infobox.find_all("tr")
    # Проверяем вторую строку (если она есть)
    if len(rows) > 1:
        second_row = rows[1].find("td", {"colspan": "2"})
        if second_row:  # noqa: SIM102
            # Проверяем, что это не заголовок (<th>) и не изображение (<img>)
            if not rows[1].find("th") and not second_row.find("img"):
                deepest_span = second_row.find_all("span")  # Находим последний <span>
                if deepest_span:
                    return deepest_span[-1].get_text(strip=True)
    return None


class MoviesSpider(scrapy.Spider):
    name = "movies"
    allowed_domains: ClassVar[list[str]] = ["ru.wikipedia.org"]
    start_urls: ClassVar[list[str]] = [
        "https://ru.wikipedia.org/wiki/Категория:Фильмы_по_алфавиту",
    ]

    csv_filename = "movies.csv"

    def __init__(self, **kwargs: Any):
        """Создаем пустой CSV-файл."""
        super().__init__(**kwargs)
        df = pd.DataFrame(columns=["title", "original_title", "genre", "director", "country", "year", "imdb_rating"])
        df.to_csv(self.csv_filename, index=False, encoding="utf-8-sig")

    def parse(self, response):
        """Собираем ссылки на фильмы, проверяем корректность страницы."""
        if not response.css("div#mw-pages"):
            self.logger.warning(f"Ошибка загрузки: {response.url}")
            yield Request(url=response.url, callback=self.parse, dont_filter=True)

        soup = BeautifulSoup(response.text, "lxml")
        columns = soup.find("div", {"class": "mw-category-columns"})

        if columns:
            # Собираем ссылки на фильмы
            for _, movie_link in enumerate(columns.find_all("a")):
                movie_link_full = "https://ru.wikipedia.org" + movie_link.get("href")
                yield response.follow(movie_link_full, callback=self.parse_movie)

        # Пагинация - продолжаем, если есть ссылка с текстом "Следующая страница"
        next_page = response.css("div#mw-pages a::text").getall()
        next_page_links = response.css("div#mw-pages a::attr(href)").getall()

        for i, link_text in enumerate(next_page):
            if "Следующая страница" in link_text:
                yield response.follow(next_page_links[i], self.parse)
                break

    def parse_movie(self, response):
        """Собираем данные о фильме."""
        soup = BeautifulSoup(response.text, "html.parser")

        # Заголовок страницы
        title_element = soup.find("h1", class_="firstHeading")

        if not title_element:
            self.logger.warning(f"Ошибка загрузки страницы фильма: {response.url}")
            yield Request(url=response.url, callback=self.parse_movie, dont_filter=True)
            return

        title = title_element.text.strip() if title_element else None

        # Инфобокс (таблица с данными о фильме)
        infobox = soup.find("table", class_="infobox")

        original_title = get_original_title(infobox)
        if not original_title:
            # Если оригинального названия нет, то пытаемся извлечь его из названия
            clean_title = None
            if '(фильм' in title:
                # Удаляем "(фильм)", т.к. он будет лишним для поиска в IMDb
                clean_title = re.sub(r"\s*\(фильм[^)]*\)", "", title)
            if clean_title:
                original_title = clean_title
            else:
                original_title = title

        # Получаем жанр, страну и режиссёра
        genre = get_list_from_infobox("Жанр", infobox)
        country = get_list_from_infobox("Стран", infobox)
        director = get_list_from_infobox("Режиссёр", infobox)

        # Год выхода
        year = get_infobox_value("Год", infobox)
        if not year:
            year = get_infobox_value("Дата выхода", infobox)
        if not year:
            year = get_infobox_value("Первый показ", infobox)
        if year:
            match = re.search(r"\b\d{4}\b", year)
            year = match.group(0) if match else None

        # Получаем рейтинг IMDb
        imdb_link = get_infobox_imdb_link(infobox)

        original_title_search = original_title
        russian_title_search = title

        # Если есть год, то добавляем в поисковый запрос, чтобы не ошибиться с фильмом со схожим названием
        if year:
            original_title_search = f"{original_title} ({year})"
            russian_title_search = f"{title} ({year})"

        imdb_rating = self.get_imdb_rating(original_title_search, imdb_link)
        if not imdb_rating:
            imdb_rating = self.get_imdb_rating(russian_title_search, imdb_link)

        # Данные о фильме
        movie_data = {
            'title': title,
            'original_title': original_title,
            'genre': ", ".join(genre),
            'director': ", ".join(director),
            'country': ", ".join(country),
            'year': year,
            'imdb_rating': imdb_rating,
        }

        # Сохраняем в CSV
        self.save_to_csv(movie_data)

        yield movie_data

    def get_imdb_rating(self, movie_title, imdb_link=None):
        """Функция для получения рейтинга IMDb."""
        search_url = f"https://www.imdb.com/find/?q={movie_title}&s=tt"
        headers = {"User-Agent": "Mozilla/5.0"}

        if not imdb_link:
            response = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            # Получаем ссылку на первый найденный фильм
            first_result = soup.find("a", {"class": "ipc-metadata-list-summary-item__t"})

            if first_result:
                href = "https://www.imdb.com" + first_result["href"]

                if "imdb.com/title/" in href:
                    imdb_link = re.search(r"https://www.imdb.com/title/tt\d+", href)
                    if imdb_link:
                        imdb_link = imdb_link.group(0)

        if not imdb_link:
            return None

        # Запрашиваем IMDb-страницу
        imdb_response = requests.get(imdb_link, headers=headers, timeout=10)
        imdb_soup = BeautifulSoup(imdb_response.text, "html.parser")

        # Проверяем, действительно ли мы на IMDb (поиск логотипа IMDb)
        if not imdb_soup.find("a", {"id": "home_img_holder"}):
            self.logger.warning(f"Ошибка загрузки страницы IMDb: {imdb_link}")
            return self.get_imdb_rating(movie_title)  # Повторный запрос

        # Извлекаем рейтинг
        rating_element = imdb_soup.find("div", {"data-testid": "hero-rating-bar__aggregate-rating__score"})
        if rating_element:
            return rating_element.text.strip().split("/")[0]  # Оставляем только число рейтинга

        return None

    def save_to_csv(self, new_data):
        """Добавляет фильм в CSV-файл, если он еще не сохранен."""
        df = pd.read_csv(self.csv_filename, encoding="utf-8-sig")
        new_raw = pd.DataFrame([new_data])

        # Проверяем, есть ли фильм уже в таблице
        if (not df[df["title"] == new_raw["title"].iloc[0]].empty or
                new_raw["title"].iloc[0] == "Категория:Телефильмы по алфавиту"):
            return

        df = pd.concat([df, new_raw], ignore_index=True)

        # Сохраняем в файл
        df.to_csv(self.csv_filename, index=False, encoding="utf-8-sig")
