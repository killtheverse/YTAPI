from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import UserQuery, SearchQuery, YTVideo
from .serializers import VideoSerializer
from datetime import datetime
import requests


@shared_task(name='fetch_videos')
def fetch_videos():
    
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'maxResults': 20,
        'type': 'video',
        'order': 'date',
        'key': settings.YOUTUBE_API_KEY,
    }

    user_queries = UserQuery.objects.all()
    for query in user_queries:
        params['q'] = query.query
        r = requests.get(search_url, params=params).json()
        results = r['items']
        video_objs = []
        for result in results:
            video_data = {}
            video_data['video_id'] = result['id']['videoId']
            video_data['publish_time'] = datetime.strptime(result['snippet']['publishTime'], '%Y-%m-%dT%H:%M:%SZ')
            video_data['channel_title'] = result['snippet']['channelTitle']
            video_data['channel_id'] = result['snippet']['channelId']
            video_data['video_title'] = result['snippet']['title']
            video_data['video_description'] = result['snippet']['description']
            
            if YTVideo.objects.raw({'video_id': video_data['video_id']}).count()==0:
                serializer = VideoSerializer(data=video_data)
                if serializer.is_valid():
                    video = serializer.save()
                    video_objs.append(video)
                else:
                    print(serializer.errors)
            else:
                video = YTVideo.objects.get({'video_id': video_data['video_id']})
                serializer = VideoSerializer(video, data=video_data)
                if serializer.is_valid():
                    video = serializer.save()
                    video_objs.append(video)
                else:
                    print(serializer.errors)
                    
        search_queries = SearchQuery.objects.raw({'query': query.query})
        if search_queries.count()==0:
            search_query = SearchQuery(
                query = query.query,
                time_created = timezone.now(),
                time_updated = timezone.now(),
                videos = video_objs
            )
            search_query.save()
        else:
            search_query = search_queries.first()
            search_query.time_updated = timezone.now()
            search_query.videos = video_objs
            search_query.save()
            
        


