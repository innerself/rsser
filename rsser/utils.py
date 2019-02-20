import os

from decouple import config
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


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
            f'{config("STATIC_DIR")}/rsser/img/gm_logo_template.png'
        )
    )

    fnt = ImageFont.truetype(
        os.path.join(
            settings.BASE_DIR,
            f'{config("STATIC_DIR")}/rsser/img/Ubuntu-Bold.ttf'
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
