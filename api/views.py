from django.db import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import serializers, status
from django.conf import settings
from .models import (
    SearchQuery, UserQuery, YTVideo
)
from .serializers import VideoSerializer
from datetime import datetime
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

        UserQuery.objects.create(user=user, query=query)
        return Response({"Message": "Query stored"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"Message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_query_results(request):
    try:
        query = request.query_params.get('query')
        number = int(request.query_params.get('number'))
    except:
        return Response({"Message": "Invalid parameters"}, status=status.HTTP_400_BAD_REQUEST)

    if number > 20:
        return Response({"Message": "Number exceeding 20"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        search_query = SearchQuery.objects.get(query=query)
    except:
        Response({"Message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)

    data = {}
    data['query'] = query
    data['number'] = number
    try:
        video_list = search_query.video.order_by('-publish_time')[:number]
        serializer = VideoSerializer(video_list, many=True)
        data['videos'] = serializer.data
    except:
        data['videos'] = []
        data['Message'] = "No video found"
    return Response(data, status=status.HTTP_200_OK)
    
