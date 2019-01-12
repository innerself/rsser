from django.core.management.base import BaseCommand

from rsser.parsers import build_rss_files


class Command(BaseCommand):
    def handle(self, *args, **options):
        build_rss_files()
