from decouple import config
from PIL import Image, ImageDraw, ImageFont


def prepare_gm_image(
        program_title_ru: str,
        program_title_en: str) -> str:

    default_font_size = 22

    if len(program_title_ru) > 25:
        length_ratio = 25 / len(program_title_ru)
        font_size = int(default_font_size * length_ratio * 1.2)
    else:
        font_size = default_font_size

    image = Image.open('./static/rsser/img/gm_logo_template.png')

    fnt = ImageFont.truetype('./static/rsser/img/Ubuntu-Bold.ttf', font_size)
    title_width, _ = fnt.getsize(program_title_ru)

    draw = ImageDraw.Draw(image)
    text_start_x = int((image.width / 2) - (title_width / 2))
    text_start_y = 245
    draw.text((text_start_x, text_start_y), program_title_ru, font=fnt)

    prepared_image_path = f'{config("STATIC_DIR")}/{program_title_en}.png'
    image.save(prepared_image_path)

    return prepared_image_path


if __name__ == '__main__':
    from django.conf import settings

    # from sett

    prepare_gm_image('Подъем', 'Podyom')
