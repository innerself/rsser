import hashlib
import os
import time
from collections import namedtuple
from datetime import date, datetime
from typing import List, Optional

import dateparser
import pytz
import requests
from bs4 import BeautifulSoup, ResultSet, Tag
from decouple import config
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from requests.exceptions import InvalidURL
from tinytag import TinyTag
from transliterate import translit

from rsser.models import Station, Program, Episode, EpisodeRecord, SiteUser
from rsser.utils import prepare_gm_image


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


def clean_gm_description(raw_description: str) -> str:
    cleaned_description = str(raw_description)

    description_trash = [
        'Программа предназначена для лиц старше шестнадцати лет.',
        'Программа предназначена для лиц старше 16 лет.',
        'Программа предназначена для слушателей старше 16 лет.',
        'Программа предназначена для слушателей старше 16 лет',
        'Предназначена для слушателей старше 16 лет.',
        'Предназначена для лиц старше шестнадцати лет.',
        'Программа предназначена для слушателей старше шестнадцати лет.',
    ]

    for phrase in description_trash:
        if phrase in raw_description:
            cleaned_description = cleaned_description.replace(phrase, '')

    cleaned_description = cleaned_description.strip()

    return cleaned_description


def get_page_soup(url: str):
    time.sleep(2)
    response = requests.get(url)

    if response.status_code != 200:
        raise InvalidURL(url)

    soup = BeautifulSoup(response.content, 'html.parser')

    return soup


def parse_gm_guest(raw_guest) -> dict:
    img = raw_guest.img['src']
    name = raw_guest.find('p', {'class': 'name'}).text.strip()
    title = raw_guest.find('p', {'class': 'grey'}).text.strip()

    guest = {
        'img': img,
        'name': name,
        'title': title,
    }

    return guest


def string_hash(string: str) -> str:
    return hashlib.md5(string.encode('utf-8')).hexdigest()


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


def prepare_gm_description(guests: List[dict]) -> str:
    description = '<br>'.join([
        f"<b>{guest['name']}</b><br>{guest['title']}<br>"
        for guest
        in guests
    ])

    return description


def get_episode_date(raw_episode):
    raw_dt = raw_episode.find('div', {'class': 'time'}).span.text.strip()
    episode_date = dateparser.parse(raw_dt, ['ru'])

    if (date.today() - episode_date.date()).days < 0:
        episode_date = datetime(
            episode_date.year - 1,
            episode_date.month,
            episode_date.day
        )

    return episode_date


def get_episode_guests(raw_episode):
    raw_guests = raw_episode.find_all('a', {'class': 'person'})
    guests = [parse_gm_guest(x) for x in raw_guests]

    return guests


def get_episode_title(raw_episode, guests, program):
    try:
        title = raw_episode.find('p', {'class': 'header'}).text.strip()
        title = clean_gm_title(title)
    except AttributeError:
        if len(guests) == 1:
            title = guests[0]['name']
        else:
            title = program.title_ru

    return title


def get_record_info(raw_episode):
    try:
        file_name = raw_episode.find('a', {'class': 'download'})['download']
        file_url = raw_episode.find('a', {'class': 'download'})['href']
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


def parse_gm_episode(
        program: Program,
        raw_episode) -> Optional[Episode]:

    episode_date = get_episode_date(raw_episode)
    guests = get_episode_guests(raw_episode)
    title = get_episode_title(raw_episode, guests, program)
    record = get_record_info(raw_episode)

    episode = Episode(
        date=episode_date,
        title=f'{title} ({episode_date.date()})',
        # title=f'{raw_title} ({episode_date.date()})',
        description=prepare_gm_description(guests),
        duration=record.duration,
        guests=guests,
        file_name=record.name,
        file_url=record.url,
        file_size=record.size,
    )

    return episode


def collect_gm_raw_episodes(
        program: Program,
        date_string: str = 'this month',
        raw_episodes: List[ResultSet] = None,
        desired_episodes_num: int = 10,
        last_try: bool = False) -> List[ResultSet]:

    if not raw_episodes:
        raw_episodes = list()

    curr_date = dateparser.parse(date_string)
    url_suffix = f'?month={curr_date.month}&year={curr_date.year}'
    full_program_url = program.url + url_suffix

    time.sleep(2)
    response = requests.get(full_program_url)

    if response.status_code != 200:
        raise InvalidURL(program.url)

    soup = BeautifulSoup(response.content, 'html.parser')
    episodes_wrapper = soup.find('div', {'class': 'oneProgramPage'})
    episodes = episodes_wrapper.ul.findChildren('li', recursive=False)

    were_episodes_this_month = (
        'Выпусков в этом месяце не было'
        not in episodes[0].text
    )
    if were_episodes_this_month:
        raw_episodes.extend(episodes)

    if not last_try and len(raw_episodes) < desired_episodes_num:
        raw_episodes = collect_gm_raw_episodes(
            program=program,
            date_string='last month',
            raw_episodes=raw_episodes,
            last_try=True,
        )

    return raw_episodes


def parse_gm_episodes(program: Program) -> List[Episode]:
    raw_episodes = collect_gm_raw_episodes(program)

    parsed_episodes = []
    for raw_episode in raw_episodes:
        parsed_episode = parse_gm_episode(program, raw_episode)

        if parsed_episode:
            parsed_episodes.append(parsed_episode)

    return parsed_episodes


def prepare_gm_title(
        program: Program,
        episode: Episode) -> str:

    if not episode.title:
        episode.title += program.title_ru

    episode.title += f' ({episode.date})'

    return episode.title


def collect_gm_raw_programs(root_url: str):
    soup = get_page_soup(root_url)
    programs_root = soup.find('div', {'id': 'programs'})
    programs_wrapper = programs_root.findAll('ul', {'class': 'programsList'})

    raw_programs = list()

    for program in programs_wrapper:
        raw_programs.extend(program.findAll('li'))

    return raw_programs


def ru_title_to_en(name):
    translited = translit(name, 'ru', reversed=True)
    cleaned = ''

    for char in translited.lower().strip():
        if char.isalnum():
            cleaned += char
        elif char == ' ':
            cleaned += '_'

    return cleaned


def parse_gm_program(station: Station, raw_program: Tag) -> Program:
    # TODO replace 'replace'
    program_url = raw_program.find('a')['href'].replace('/broadcasts/', '')
    full_url = station.programs_root + program_url
    program_page_soup = get_page_soup(full_url)

    name = clean_gm_title(
        program_page_soup.find('div', {'class', 'pageHeader'}).h1.text
    )

    program_about_soup = program_page_soup.find(
        'div', {'class', 'aboutProgram'}
    )

    description = program_about_soup.find(
        'div', {'class', 'textDescribe'}
    ).findAll('p')[-1].text.strip()

    if not description:
        description = name

    description = clean_gm_description(description)

    # TODO decide how to parse hosts
    # hosts = parse_gm_hosts()
    # hosts = list(raw_program.find('a'))[-1].strip().split(' и ')

    program_en_title = ru_title_to_en(name)

    feeds_root = f'{config("ROOT_URL")}/feeds/{station.short_latin_name}'
    feed_url = f'{feeds_root}/{program_en_title}.xml'

    program = Program(
        title_ru=name,
        title_en=program_en_title,
        description=description,
        url=full_url,
        station=station,
        feed_url=feed_url,
    )

    return program


def parse_gm_programs(station: Station):
    raw_programs = collect_gm_raw_programs(station.programs_root)
    programs = [
        parse_gm_program(station, raw_program)
        for raw_program
        in raw_programs
    ]

    return programs


def notify_programs_status_change(station: Station) -> bool:
    sender = config("EMAIL_FROM")
    recipients = [
        user.email
        for user
        in SiteUser.objects.filter(notify=True).all()
    ]
    subject = 'Изменения в списке программ'

    new_programs = station.programs.filter(status='new')
    archive_programs = station.programs.filter(status='archive')

    if not any([new_programs, archive_programs]):
        return False

    context = {
        'station_name': station.name,
        'new_programs': new_programs,
        'archive_programs': archive_programs,
    }

    text_tmpl = get_template('rsser/program_status_change.txt')
    html_tmpl = get_template('rsser/program_status_change.html')

    text_content = text_tmpl.render(context)
    html_content = html_tmpl.render(context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=sender,
        to=recipients,
    )
    message.attach_alternative(html_content, 'text/html')

    message_sent = message.send()

    return bool(message_sent)


def update_gm_programs() -> None:
    station = Station.objects.filter(name='Говорит Москва').first()

    for program in station.programs.all():
        program.status = 'archive'
        program.save()

    programs = parse_gm_programs(station)

    for program in programs:
        if 'повтор' in program.title_ru:
            continue

        existing_program = Program.objects.filter(
            title_ru=program.title_ru
        ).first()

        if existing_program:
            existing_program.status = 'current'
            # existing_program.hosts = program.hosts
            existing_program.save()
        else:
            program.status = 'new'
            program.save()

    mail_sent = notify_programs_status_change(station)

    if mail_sent:
        station.programs.filter(status='archive').delete()

    return None


def collect_feed_entry(
        program: Program,
        episode: Episode) -> FeedEntry:

    minutes, seconds = divmod(episode.duration, 60)
    hours, minutes = divmod(minutes, 60)
    duration = '%02d:%02d:%02d' % (hours, minutes, seconds)

    entry = FeedEntry()
    entry.load_extension('podcast')

    entry.title(episode.title)
    entry.link(href=program.url)
    entry.description(episode.description)
    entry.published(pytz.utc.localize(episode.date))
    entry.guid(string_hash(episode.file_url))
    entry.enclosure(episode.file_url, str(episode.file_size), 'audio/mpeg')
    entry.podcast.itunes_duration(duration)

    return entry


def collect_feed(
        program: Program,
        episodes: List[Episode]) -> FeedGenerator:

    feed = FeedGenerator()
    feed.load_extension('podcast')

    feed.title(f'{program.title_ru} :: {program.station.name}')
    feed.link(href=program.url)
    feed.image(program.image_path)
    feed.description(program.description)
    feed.language('ru')
    # feed.author(program.station.name)

    for episode in episodes:
        entry = collect_feed_entry(program, episode)
        feed.add_entry(entry, order='append')

    return feed


def parse_gm(station: Station) -> None:
    for program in station.programs.all():
        if not program.image_path:
            image_path = prepare_gm_image(program.title_ru, program.title_en)
            program.image_path = image_path
            program.save()

        episodes = parse_gm_episodes(program)
        feed = collect_feed(program, episodes)

        file_name = os.path.join(
            settings.BASE_DIR,
            'rsser',
            'feeds',
            'gm',
            f'{program.title_en}.xml',
        )

        feed.rss_file(file_name, pretty=True)

    return None


def update_programs():
    stations = Station.objects.all()
    updaters = {
        'Говорит Москва': update_gm_programs,
    }

    for station in stations:
        updaters[station.name]()

    return None


def build_rss_files():
    stations = Station.objects.all()
    parsers = {
        'Говорит Москва': parse_gm,
    }

    for station in stations:
        parsers[station.name](station)

    return None
