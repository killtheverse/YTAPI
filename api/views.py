from re import search
from django.db import models
from pymongo import DESCENDING
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import serializers, status
from django.conf import settings
from .models import (
    SearchQuery, UserQuery, YTVideo
)
from pymodm.queryset import QuerySet
from .serializers import VideoSerializer
from datetime import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
from authentication.views import get_user_from_token
import requests

@api_view(['GET'])
def greeter(request):
    return Response("Hello world")


@api_view(['POST'])
def post_query(request):
    
    try:
        query = request.POST['query']
        if len(query)==0:
            return Response({"Message":"Empty Query"}, status=status.HTTP_400_BAD_REQUEST)
        elif len(query)>100:
            return Response({"Message":"Query length exceeded 100"}, status=status.HTTP_400_BAD_REQUEST)
        
        authorization_header = request.headers.get('Authorization')
        access_token = authorization_header.split(' ')[1]
        user = get_user_from_token(access_token)
        user_query = UserQuery(
            user = user,
            query = query,
            time_created = timezone.now()
        )
        user_query.save()
        return Response({"Message": "Query stored"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"Message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_query_results(request):
    try:
        query = request.query_params.get('query')
        number = int(request.query_params.get('number', 5))
    except:
        return Response({"Message": "Invalid parameters"}, status=status.HTTP_400_BAD_REQUEST)

    if number > 20 or number<=0:
        return Response({"Message": "Number should be between 1 and 20"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        search_query = SearchQuery.objects.get({'query': query})
    except:
        return Response({"Message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)

    data = {}
    data['query'] = query
    data['number'] = number
    try:
        search_query_videos = search_query.videos
        video_ids = [video._id for video in search_query_videos]
        video_list = list(YTVideo.objects.raw({'_id': {'$in': video_ids}}).order_by([('publish_time', DESCENDING)]).limit(number))
        serializer = VideoSerializer(video_list, many=True)
        data['videos'] = serializer.data
    except:
        data['videos'] = []
        data['Message'] = "No video found"
    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
def update_videos(request):
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
                print("creating")
                serializer = VideoSerializer(data=video_data)
                if serializer.is_valid():
                    video = serializer.save()
                    video_objs.append(video)
                else:
                    print(serializer.errors)
                    print(video_data)
            else:
                print("updating")
                video = YTVideo.objects.get({'video_id': video_data['video_id']})
                serializer = VideoSerializer(video, data=video_data)
                if serializer.is_valid():
                    video = serializer.save()
                    video_objs.append(video)
                else:
                    print(serializer.errors)
                    print(video_data)
                    
        search_queries = SearchQuery.objects.raw({'query': query.query})
        print(len(video_objs))
        if search_queries.count()==0:
            print("=======================================")
            print("new query")
            search_query = SearchQuery(
                query = query.query,
                time_created = timezone.now(),
                time_updated = timezone.now(),
                videos = video_objs
            )
            search_query.save()
        else:
            print("updating query")
            search_query = search_queries.first()
            search_query.time_updated = timezone.now()
            search_query.videos = video_objs
            search_query.save()
    return Response("OK")
