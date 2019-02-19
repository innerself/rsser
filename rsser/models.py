from dataclasses import dataclass
from datetime import datetime
from typing import List

from django.db import models


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


class EpisodeRecord(models.Model):
    url = models.URLField()
    url_hash = models.CharField(max_length=200)
    duration = models.IntegerField()
    size = models.IntegerField()
    added = models.DateField(auto_now_add=True)


@dataclass
class Episode:
    date: datetime
    title: str
    description: str
    duration: int
    persons: List[dict]
    file_name: str
    file_url: str
    file_size: int
