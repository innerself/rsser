import hashlib
import os
import time

import requests
from decouple import config
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
from django.db import models
from requests.exceptions import InvalidURL
from tinytag import TinyTag


def prepare_gm_image(
        program_title_ru: str,
        program_title_en: str) -> str:

    default_font_size = 26

    if len(program_title_ru) > 25:
        length_ratio = 25 / len(program_title_ru)
        font_size = int(default_font_size * length_ratio * 1.2)
    else:
        font_size = default_font_size

    image = Image.open(
        os.path.join(
            settings.BASE_DIR,
            f'{config("STATIC_DIR")}/rsser/images/gm_logo_template.png'
        )
    )

    fnt = ImageFont.truetype(
        os.path.join(
            settings.BASE_DIR,
            f'{config("STATIC_DIR")}/rsser/images/Ubuntu-Bold.ttf'
        ),
        font_size
    )

    title_width, _ = fnt.getsize(program_title_ru)

    draw = ImageDraw.Draw(image)
    text_start_x = int((image.width / 2) - (title_width / 2))
    text_start_y = 245
    draw.text((text_start_x, text_start_y), program_title_ru, font=fnt)

    image_file_name = f'{program_title_en}.png'
    prepared_image_path = f'{config("STATIC_DIR")}/rsser/images/{image_file_name}'
    image.save(prepared_image_path)

    image_url = f'{config("SITE_URL")}/images/{image_file_name}'

    return image_url


def file_info(url: str, file_name: str) -> tuple:
    url_hash = string_hash(url)
    episode = EpisodeRecord.objects.filter(url_hash=url_hash).first()

    if episode:
        return episode.duration, episode.size

    tmp_folder_name = 'uploads'
    tmp_folder = os.path.join(settings.BASE_DIR, tmp_folder_name)
    tmp_file = os.path.join(tmp_folder, file_name)

    if not os.path.exists(tmp_folder):
        os.mkdir(tmp_folder)

    time.sleep(2)
    response = requests.get(url)

    if not response.status_code == 200:
        raise InvalidURL(url)

    with open(tmp_file, 'wb') as f:
        f.write(response.content)

    tag = TinyTag.get(tmp_file)

    EpisodeRecord.objects.create(
        url=url,
        url_hash=url_hash,
        duration=tag.duration,
        size=tag.filesize,
    )

    os.remove(tmp_file)

    return int(tag.duration), tag.filesize


def clean_gm_title(raw_title: str) -> str:
    if not raw_title.startswith('«') and not raw_title.endswith('»'):
        return raw_title

    unbalanced_quotes = raw_title.count('«') - raw_title.count('»') > 0

    if unbalanced_quotes:
        title = raw_title[1:]
    else:
        title = raw_title[1:-1]

    title = title.replace(' (16+)', '').replace(' (0+)', '')

    return title


class EpisodeRecord(models.Model):
    url = models.URLField()
    url_hash = models.CharField(max_length=200)
    duration = models.IntegerField()
    size = models.IntegerField()
    added = models.DateField(auto_now_add=True)


def string_hash(string: str) -> str:
    return hashlib.md5(string.encode('utf-8')).hexdigest()