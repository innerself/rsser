from bs4 import BeautifulSoup
from django.test import TestCase

from rsser import parsers


class GmParserTests(TestCase):

    def test_clean_gm_title(self):
        f = parsers.clean_gm_title
        self.assertEqual(f('«some text»'), 'some text')
        self.assertEqual(f('«some «text»»'), 'some «text»')
        self.assertEqual(f('«some «text»'), 'some «text»')

    def test_parse_gm_guest(self):
        f = parsers.parse_gm_guest

        raw_guest = (
            '<a class="person" href="/users/guests/1062/">'
            '<div class="personPic">'
            '<img alt="" src="https://some-link.jpg"/>'
            '</div>'
            '<div class="information">'
            '<p class="name">Валерий Рейнгольд</p>'
            '<p class="grey">Ветеран футбольного клуба "Спартак"</p>'
            '</div>'
            '</a>'
        )

        soup = BeautifulSoup(raw_guest, 'html.parser')

        self.assertEqual(f(soup), {
            'img': 'https://some-link.jpg',
            'name': 'Валерий Рейнгольд',
            'title': 'Ветеран футбольного клуба "Спартак"',
        })

    def test_string_hash(self):
        f = parsers.string_hash
        self.assertEqual(f('qwe'), '76d80224611fc919a5d54f0ff9fba446')

    # def test_file_info(self):
    #     f = parsers.file_info
    #
    #     pass

    def test_prepare_gm_description(self):
        f = parsers.prepare_gm_description
        self.assertEqual(f([]), '')  # TODO am I sure?
        self.assertEqual(f([
            {
                'img': 'https://some-link.jpg',
                'name': 'Валерий Рейнгольд',
                'title': 'Ветеран футбольного клуба "Спартак"',
            }
        ]), (
                '<b>Валерий Рейнгольд</b><br>'
                'Ветеран футбольного клуба "Спартак"<br>'
            )
        )
        self.assertEqual(f([
            {
                'img': 'https://some-link.jpg',
                'name': 'Валерий Рейнгольд',
                'title': 'Ветеран футбольного клуба "Спартак"',
             },
            {
                'img': 'https://some-link.jpg',
                'name': 'Дарья Шишканова',
                'title': 'Спортивный агент',
            }
        ]), (
                '<b>Валерий Рейнгольд</b><br>'
                'Ветеран футбольного клуба "Спартак"<br><br>'
                '<b>Дарья Шишканова</b><br>Спортивный агент<br>'
            )
        )
