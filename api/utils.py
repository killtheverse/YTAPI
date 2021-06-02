from elasticsearch.helpers import bulk
from elasticsearch import Elasticsearch
from .models import YTVideo
from .search import Video
from django.conf import settings


def slugify(input):
    return input.lower().replace(" ", "-")


def bulk_indexing():
    Video.init(index='video_index')
    es = Elasticsearch([settings.ELASTIC_SEARCH_URL])
    bulk(client=es, actions=(video.indexing() for video in YTVideo.objects.all()))
