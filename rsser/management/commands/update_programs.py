from django.core.management.base import BaseCommand

from rsser.parsers import update_programs


class Command(BaseCommand):
    def handle(self, *args, **options):
        update_programs()
