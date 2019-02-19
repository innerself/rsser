from django.http import HttpResponse
from django.shortcuts import render


from django.shortcuts import render

from rsser.models import Station, Program
from rsser.parsers import build_rss_files, update_gm_programs


def index(request):
    context = {
        'stations': Station.objects.all(),
    }

    return render(request, 'rsser/index.html', context)
