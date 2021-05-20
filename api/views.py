from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import requests

@api_view(['GET'])
def greeter(request):
    return Response("Hello world")
    
    
@api_view(['GET'])
def hello(request):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': 'hello',
        'maxResults': 10,
        'type': 'video',
        'order': 'date',
        'key': settings.YOUTUBE_API_KEY,

    }
    r = requests.get(search_url, params=params).json()
    results = r['items']
    data = []
    for result in results:
        result_obj = {}
        result_obj['video_id'] = result['id']['videoId']
        result_obj['publish_time'] = result['snippet']['publishTime']
        result_obj['channel_title'] = result['snippet']['channelTitle']
        result_obj['video_title'] = result['snippet']['title']
        result_obj['video_description'] = result['snippet']['description']
        data.append(result_obj)
    
    response = {}
    response['data'] = data
    return Response(response, status=status.HTTP_200_OK)
    
