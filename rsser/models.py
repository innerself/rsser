from collections import namedtuple
import datetime

import dateparser
from django.db import models
from requests.exceptions import InvalidURL

from rsser.utils import file_info, clean_gm_title


class Station(models.Model):
    name = models.CharField('name', max_length=100)
    short_latin_name = models.CharField('short latin name', max_length=30)
    url = models.URLField('url')
    logo = models.URLField()
    programs_root = models.CharField('programs root', max_length=200)

    def __str__(self):
        return self.name


class Host(models.Model):
    first_name = models.CharField('first name', max_length=50)
    last_name = models.CharField('last name', max_length=50)
    photo = models.URLField(blank=True, null=True)
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name='hosts',
    )

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


class Program(models.Model):
    class Meta:
        ordering = ['title_ru']

    STATUSES = (
        ('new', 'New'),
        ('current', 'Current'),
        ('archive', 'Archive'),
    )

    title_ru = models.CharField('name_ru', max_length=200)
    title_en = models.CharField('name_en', max_length=200)
    description = models.CharField(max_length=300)
    url = models.URLField()
    feed_url = models.URLField()
    image_path = models.URLField()
    status = models.CharField(max_length=1, choices=STATUSES)
    hosts = models.ManyToManyField(Host, related_name='programs')
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name='programs',
    )

    def __str__(self):
        return self.title_ru


class SiteUser(models.Model):
    email = models.EmailField(null=False, blank=False)
    notify = models.BooleanField(default=False)

    def __str__(self):
        return self.email


class Episode:
    def __init__(self, program, html):
        self.program = program
        self.html = html
        self.date = None
        self.guests = None
        self.title = None
        self.record = None
        self.description = None

    def parse(self):
        self.date = self._parse_date()
        self.guests = self._parse_guests()
        self.title = self._parse_title()
        self.record = self._parse_record()
        self.description = self._parse_description()

    def _parse_date(self):
        raw_dt = self.html.find('div', {'class': 'time'}).span.text.strip()
        parsed_date = dateparser.parse(raw_dt, ['ru'])

        if (datetime.date.today() - parsed_date.date()).days < 0:
            parsed_date = datetime.datetime(
                parsed_date.year - 1,
                parsed_date.month,
                parsed_date.day
            )

        return parsed_date

    @staticmethod
    def _parse_guest(raw_guest):
        img = raw_guest.img['src']
        name = raw_guest.find('p', {'class': 'name'}).text.strip()
        title = raw_guest.find('p', {'class': 'grey'}).text.strip()

        guest = {
            'img': img,
            'name': name,
            'title': title,
        }

        return guest

    def _parse_guests(self):
        raw_guests = self.html.find_all('a', {'class': 'person'})
        guests = [self._parse_guest(guest) for guest in raw_guests]

        return guests

    def _parse_title(self):
        try:
            title = self.html.find('p', {'class': 'header'}).text.strip()
            title = clean_gm_title(title)
        except AttributeError:
            if len(self.guests) == 1:
                title = self.guests[0]['name']
            else:
                title = self.program.title_ru

        title = f'{title} ({self.date.date()})'

        return title

    def _parse_record(self):
        try:
            file_name = self.html.find('a', {'class': 'download'})['download']
            file_url = self.html.find('a', {'class': 'download'})['href']
        except TypeError:
            return None

        # if not file_name or not file_url:
        #     return None

        try:
            duration, file_size = file_info(file_url, file_name)
        except InvalidURL:
            return None

        Record = namedtuple('Record', ('name', 'url', 'duration', 'size'))
        record = Record(
            name=file_name,
            url=file_url,
            duration=duration,
            size=file_size,
        )

        return record

    def _parse_description(self):
        description = '<br>'.join([
            f"<b>{guest['name']}</b><br>{guest['title']}<br>"
            for guest
            in self.guests
        ])

        return description



# @dataclass
# class Episode:
#     date: datetime
#     title: str
#     description: str
#     duration: int
#     guests: List[dict]
#     file_name: str
#     file_url: str
#     file_size: int
