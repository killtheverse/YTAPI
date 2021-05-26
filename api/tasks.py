from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import SearchQuery, YTVideo
from .serializers import VideoSerializer
from datetime import datetime, timedelta
import requests


@shared_task(name='fetch_videos')
def fetch_videos():
    last_hour_time = datetime.now() - timedelta(hours=1)
    search_queries = SearchQuery.objects.raw({'time_updated': {'$lte': last_hour_time}})
    for search_query in search_queries:
        fetch_single_video.delay(search_query.query)


@shared_task()
def fetch_single_video(query):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "maxResults": 20,
        "type": "video",
        "order": "date",
        "q": query,
        "key": settings.YOUTUBE_API_KEY,
    }
    
    r = requests.get(search_url, params=params).json()
    video_keys = []
    video_data = {}
    for result in  r["items"]:
        video_keys.append(result["id"]["videoId"])
        video_data[result["id"]["videoId"]] = {
            "publish_time": datetime.strptime(result["snippet"]["publishTime"], "%Y-%m-%dT%H:%M:%SZ"),
            "channel_title": result["snippet"]["channelTitle"],
            "channel_id": result["snippet"]["channelId"],
            "video_title": result["snippet"]["title"],
            "video_description": result["snippet"]["description"]
        }

    video_objs = []    
    existing_videos = YTVideo.objects.raw({"_id": {"$in": video_keys}})
    existing_video_ids = []
    for existing_video in existing_videos:
        existing_video_ids.append(existing_video._id)
        serializer = VideoSerializer(existing_video, video_data[existing_video.video_id])
        if serializer.is_valid():
            video_obj = serializer.save()
            video_objs.append(video_obj)
        else:
            print(serializer.errors)
    
    new_videos = []
    for key, val in video_data.items():
        if key in existing_video_ids:
            continue
        new_video_obj = YTVideo(
            video_id = key,
            video_title = val["video_title"],
            video_description = val["video_description"],
            channel_title = val["channel_title"],
            channel_id = val["channel_id"],
            publish_time = val["publish_time"],
            time_created = timezone.now(),
            time_updated = timezone.now(),
        )
        new_videos.append(new_video_obj)
    
    new_videos = YTVideo.objects.bulk_create(new_videos)

    video_objs.extend(new_videos)
    search_query = SearchQuery.objects.get({'query': query})
    search_query.videos = video_objs
    search_query.time_updated = timezone.now()
    search_query.save()

