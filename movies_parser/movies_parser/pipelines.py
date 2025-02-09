# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import csv
from pathlib import Path

import pandas as pd
from itemadapter import ItemAdapter  # noqa: F401
from scrapy.exceptions import DropItem


class DuplicateItemError(DropItem):
    def __init__(self, title):
        super().__init__(f"Дубликат: '{title}'")


class DuplicatePipeline:
    def __init__(self):
        self.titles_seen = set()

    def open_spider(self, spider):  # noqa: ARG002
        try:
            df = pd.read_csv('movies.csv', encoding='utf-8')
            self.titles_seen = set(df['title'].tolist())
        except FileNotFoundError:
            self.titles_seen = set()

    def process_item(self, item, spider):  # noqa: ARG002
        if item['title'] in self.titles_seen:
            raise DuplicateItemError(item['title'])

        self.titles_seen.add(item['title'])
        return item


class MoviesParserPipeline:
    def __init__(self):
        self.file = None
        self.writer = None

    def open_spider(self, spider):  # noqa: ARG002
        self.file = Path('movies.csv').open('a+', newline='', encoding='utf-8')  # noqa: SIM115
        self.writer = csv.writer(self.file)

        if self.file.tell() == 0:
            self.writer.writerow(['title', 'original_title', 'genre', 'director', 'country', 'year', 'imdb_rating'])

    def process_item(self, item, spider):  # noqa: ARG002

        self.writer.writerow([
            item['title'],
            item['original_title'],
            item['genre'],
            item['director'],
            item['country'],
            item['year'],
            item['imdb_rating'],
        ])
        return item

    def close_spider(self, spider):  # noqa: ARG002
        self.file.close()
