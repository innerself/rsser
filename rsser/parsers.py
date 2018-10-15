import hashlib
import os
from typing import List, Optional

import dateparser
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from requests.exceptions import InvalidURL
from tinytag import TinyTag

from rsser.models import Station, Program, ParsedEpisode, Episode


def clean_gm_title(raw_title: str) -> str:
    if not raw_title.startswith('«') and not raw_title.endswith('»'):
        return raw_title

    unbalanced_quotes = raw_title.count('«') - raw_title.count('»') > 0

    if unbalanced_quotes:
        title = raw_title[1:]
    else:
        title = raw_title[1:-1]

    return title


def parse_gm_person(raw_person) -> dict:
    img = raw_person.img['src']
    name = raw_person.find('p', {'class': 'name'}).text.strip()
    title = raw_person.find('p', {'class': 'grey'}).text.strip()

    person = {
        'img': img,
        'name': name,
        'title': title,
    }

    return person


def file_info(url: str, file_name: str) -> tuple:
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    episode = Episode.objects.filter(url_hash=url_hash).first()

    if episode:
        return episode.duration, episode.size

    tmp_folder_name = 'uploads'
    tmp_folder = os.path.join(settings.BASE_DIR, tmp_folder_name)
    tmp_file = os.path.join(tmp_folder, file_name)

    if not os.path.exists(tmp_folder):
        os.mkdir(tmp_folder)

    response = requests.get(url)

    if not response.status_code == 200:
        raise InvalidURL(url)

    with open(tmp_file, 'wb') as f:
        f.write(response.content)

    tag = TinyTag.get(tmp_file)

    Episode.objects.create(
        url_hash=url_hash,
        duration=tag.duration,
        size=tag.filesize,
    )

    os.remove(tmp_file)

    return int(tag.duration), tag.filesize


def parse_gm_episode(raw_episode) -> Optional[ParsedEpisode]:
    raw_dt = raw_episode.find('div', {'class': 'time'}).span.text.strip()

    try:
        raw_title = raw_episode.find('p', {'class': 'header'}).text.strip()
    except AttributeError:
        raw_title = ''

    file_name = raw_episode.find('a', {'class': 'download'})['download']
    file_url = raw_episode.find('a', {'class': 'download'})['href']

    if not file_name or not file_url:
        return None

    raw_persons = raw_episode.find_all('a', {'class': 'person'})

    parsed_persons = []
    for raw_person in raw_persons:
        parsed_person = parse_gm_person(raw_person)
        parsed_persons.append(parsed_person)

    try:
        duration, file_size = file_info(file_url, file_name)
    except InvalidURL:
        return None

    episode = ParsedEpisode(
        date=dateparser.parse(raw_dt, ['ru']).date(),
        title=clean_gm_title(raw_title),
        duration=duration,
        persons=parsed_persons,
        file_name=file_name,
        file_url=file_url,
        file_size=file_size,
    )

    return episode


def parse_gm_episodes(program: Program) -> List[ParsedEpisode]:
    response = requests.get(program.url)

    if response.status_code != 200:
        raise InvalidURL(program.url)

    soup = BeautifulSoup(response.content, 'html.parser')
    episodes_wrapper = soup.find('div', {'class': 'oneProgramPage'})
    raw_episodes = episodes_wrapper.ul.findChildren('li', recursive=False)

    parsed_episodes = []
    for raw_episode in raw_episodes:
        parsed_episode = parse_gm_episode(raw_episode)

        if parsed_episode:
            parsed_episodes.append(parsed_episode)

    return parsed_episodes


def parse_gm(station: Station):
    for program in station.programs.all():
        parse_gm_episodes(program)


def build_rss_files():
    stations = Station.objects.all()
    parsers = {
        'Говорит Москва': parse_gm,
    }

    for station in stations:
        parsed_station = parsers[station.name](station)
        # rss_file = buld_rss_file(parsed_station)


if __name__ == '__main__':
    build_rss_files()
