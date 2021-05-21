from celery import shared_task
from django.conf import settings
from .models import UserQuery, SearchQuery, YTVideo
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
            video_id = result['id']['videoId']
            publish_time = datetime.strptime(result['snippet']['publishTime'], '%Y-%m-%dT%H:%M:%SZ')
            channel_title = result['snippet']['channelTitle']
            video_title = result['snippet']['title']
            video_description = result['snippet']['description']
            
            videos = YTVideo.objects.filter(video_id=video_id)
            if not videos.exists():
                video_obj = YTVideo(
                    video_id=video_id,
                    publish_time=publish_time,
                    channel_title=channel_title,
                    video_title=video_title,
                    video_description=video_description 
                    )
                video_objs.append(video_obj)
                video_obj.save()
            else:
                video_objs.append(videos.first())
        
        search_list = SearchQuery.objects.filter(query=query.query)
        search_query_obj = None
        if search_list.exists():
            search_query_obj = search_list.first()
            search_query_obj.video.clear()
        else:
            search_query_obj = SearchQuery(query=query.query)
            search_query_obj.save()
        for video in video_objs:
            search_query_obj.video.add(video)
        


