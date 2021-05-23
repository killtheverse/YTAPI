from pymongo import DESCENDING
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import (
    SearchQuery, UserQuery, YTVideo
)
from .serializers import VideoSerializer
from django.utils import timezone
from authentication.views import get_user_from_token
from .tasks import fetch_single_video
from bson import ObjectId


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
        
        user_obj_id = ObjectId(user._id)
        query_obj = UserQuery.objects.raw({'user': user_obj_id, 'query': query})
        if query_obj.count() == 0:
            user_query = UserQuery(
                user = user,
                query = query,
                time_created = timezone.now()
            )
            user_query.save()
        
        fetch_single_video.delay(query)
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
    
    authorization_header = request.headers.get('Authorization')
    access_token = authorization_header.split(' ')[1]
    user = get_user_from_token(access_token)
    user_object_id = ObjectId(user._id)
    if UserQuery.objects.raw({'query': query, 'user': user_object_id}).count()==0:
        return Response({"Message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)

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
def get_user_queries(request):
    authorization_header = request.headers.get('Authorization')
    access_token = authorization_header.split(' ')[1]
    user = get_user_from_token(access_token)

    user_obj_id = ObjectId(user._id)
    if UserQuery.objects.raw({'user': user_obj_id}).count()>0:
        user_queries = [query.query for query in list(UserQuery.objects.raw({'user': user_obj_id}))]
        return Response({"queries": user_queries}, status=status.HTTP_200_OK)
    else:
        return Response({"Message": "No queries associated with the user"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def delete_query(request):
    authorization_header = request.headers.get('Authorization')
    access_token = authorization_header.split(' ')[1]
    user = get_user_from_token(access_token)
    query = request.POST['query']
    user_obj_id = ObjectId(user._id)
    try:
        user_query = UserQuery.objects.get({'user': user_obj_id, 'query': query})
        user_query.delete()
        return Response({"Message": "Deleted query"}, status=status.HTTP_200_OK)
    except:
        return Response({"Message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)