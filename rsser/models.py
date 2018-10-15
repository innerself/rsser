from dataclasses import dataclass
from datetime import date
from typing import List

from django.db import models
from transliterate import translit


class Station(models.Model):
    name = models.CharField('name', max_length=100)
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

    name = models.CharField('name', max_length=200)
    description = models.CharField(max_length=300)
    url = models.URLField()
    status = models.CharField(max_length=1, choices=STATUSES)
    hosts = models.ManyToManyField(Host, related_name='programs')
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name='programs',
    )

    def __str__(self):
        return self.name


class Episode(models.Model):
    url_hash = models.CharField(max_length=200)
    duration = models.IntegerField()
    size = models.IntegerField()
    added = models.DateField(auto_now_add=True)


@dataclass
class ParsedEpisode:
    date: date
    title: str
    duration: int
    persons: List[dict]
    file_name: str
    file_url: str
    file_size: int
