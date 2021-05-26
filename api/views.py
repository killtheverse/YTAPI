from os import stat
import bson
import pymongo
from authentication.models import User
from pymongo import DESCENDING
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import (
    SearchQuery, YTVideo
)
from .serializers import VideoSerializer
from django.utils import timezone
from authentication.utils import get_user_from_token
from .tasks import fetch_single_video
from bson import ObjectId
from django.template.defaultfilters import slugify


import requests
from datetime import datetime
from django.conf import settings


@api_view(['GET', 'POST'])
def query_list(request):
    '''
    List all the queries of the user or create a new query
    '''
    if request.method == "GET":
        # extract access token from header and get user
        authorization_header = request.headers.get("Authorization")
        access_token = authorization_header.split(" ")[1]
        user = get_user_from_token(access_token)
        user_id = bson.ObjectId(user._id)
        search_queries = SearchQuery.objects.raw({"users": user_id})
        queries = []
        for search_query in search_queries:
            queries.append({
                "query": search_query.query,
                "slug": search_query.slug
            })
        data = {
            "username": user.username,
            "queries": queries
        }
        if len(data["queries"])==0:
            data["message"] = "NO queries registered for the user"
        return Response(data=data, status=status.HTTP_200_OK)


    elif request.method == 'POST':
        try:
            # check if query is valid
            query = request.data.get("query", None)
            if query == None:
                return Response({"message": "Query not found"})
            if len(query)==0:
                return Response({"message":"Empty Query"}, status=status.HTTP_400_BAD_REQUEST)
            elif len(query)>100:
                return Response({"message":"Query length exceeded 100"}, status=status.HTTP_400_BAD_REQUEST)
            
            # extract access token from header and get user
            authorization_header = request.headers.get('Authorization')
            access_token = authorization_header.split(' ')[1]
            user = get_user_from_token(access_token)
            
            # check if user already has query with same name
            # if not, then create the query
            
            
            
            try:
                search_query = SearchQuery.objects.get({'query': query})
                if not user in search_query.users:
                    search_query.users.append(user)
                    search_query.save()
                else:
                    return Response({"message": "Query already exists"}, status=status.HTTP_200_OK)
            except:
                search_query = SearchQuery(
                    query = query,
                    users = [user],
                    time_created = timezone.now(),
                    slug = slugify(query),
                )
                search_query.save()

            
            # fetch the videos associated with this single query
            fetch_single_video.delay(query)
            return Response({"message": "Query stored"}, status=status.HTTP_201_CREATED)
        except:
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        


@api_view(["GET", "DELETE"])
def query_detail(request, slug):
    if request.method == "GET":
        try:
            limit = int(request.query_params.get('limit', 5))
            offset = int(request.query_params.get('offset', 0))
        except:
            return Response({"message": "Invalid query parameters"}, status=status.HTTP_400_BAD_REQUEST)

        if offset < 0 or offset >= 20:
            return Response({"message": "Offset should be between 0 and 19"}, status=status.HTTP_400_BAD_REQUEST)
        if limit < 1 or limit > 20:
            return Response({"message": "Limit should be between 1 and 20"}, status=status.HTTP_400_BAD_REQUEST)

        next_url = "127.0.0.1:8000/api/queries/"+slug+"/?limit="+str(limit)+"&offset="+str(offset+limit)

        if offset+limit >= 20:
            limit = 20-offset
            next_url = "No more data"

        try:
            search_query = SearchQuery.objects.get({"slug": slug})
        except:
            return Response({"message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)



        video_ids = [video._id for video in search_query.videos]
        
        video_list = YTVideo.objects.aggregate(
            {"$match": {"_id": {"$in": video_ids}}},
            {"$sort": {"publish_time": DESCENDING}},
            {"$skip": offset},
            {"$limit": limit}
        )
        
        serializer = VideoSerializer(video_list, many=True)
        data = {
            "query": search_query.query,
            "limit": limit,
            "offset": offset,
            "next": next_url,
            "videos": serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)


    elif request.method == "DELETE":
        
        try:
            search_query = SearchQuery.objects.get({"slug": slug})
        except:
            return Response({"message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)

        #extract the access token from the header and get user
        authorization_header = request.headers.get('Authorization')
        access_token = authorization_header.split(' ')[1]
        user = get_user_from_token(access_token)
        
        # delete the record if it exists else return the message
        if user in search_query.users:
            search_query.users.remove(user)
            search_query.save()
            return Response({"message": "User removed from query's users"}, status=status.HTTP_200_OK)
        else:
            return Response({"User has not registered this query"}, status=status.HTTP_406_NOT_ACCEPTABLE)


# @api_view(['POST'])
# def register_query(request):
#     '''
#     View which allows a user to register a query. Requires authentication

#     Request parameters:
#     - query: query which is to be searched

#     Response:
#     - On success
#         - returns a message that query has been stored
#     - On failure
#         - returns error message
#     '''

#     try:
#         # check if query is valid
#         query = request.data.get('query', None)
#         if query == None:
#             return Response({"message": "Query not found"})
#         if len(query)==0:
#             return Response({"message":"Empty Query"}, status=status.HTTP_400_BAD_REQUEST)
#         elif len(query)>100:
#             return Response({"message":"Query length exceeded 100"}, status=status.HTTP_400_BAD_REQUEST)
        
#         # extract access token from header and get user
#         authorization_header = request.headers.get('Authorization')
#         access_token = authorization_header.split(' ')[1]
#         user = get_user_from_token(access_token)
        
#         # check if user already has query with same name
#         # if not, then create the query
#         user_obj_id = ObjectId(user._id)
#         query_obj = UserQuery.objects.raw({'user': user_obj_id, 'query': query})
#         if query_obj.count() == 0:
#             user_query = UserQuery(
#                 user = user,
#                 query = query,
#                 time_created = timezone.now()
#             )
#             user_query.save()
        
#         # fetch the videos associated with this single query
#         fetch_single_video.delay(query)
#         return Response({"message": "Query stored"}, status=status.HTTP_201_CREATED)
#     except Exception as e:
#         print(e)
#         return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)


# @api_view(['GET'])
# def get_query_results(request):
#     '''
#     View which allows a user to obtain the videos associated with a query. Requires authentication

#     Request parameters(parameters should be present in url):
#     - query(Required): the query to be searched
#     - number(Required): number of videos to obtain(between 1 and 20)

#     Response:
#     - On success:
#         - query: query that was searched
#         - number: number of videos requested
#         - message(Optional): if no video is found, it returns a message
#         - videos: a list consisting of videos:
#             - video_id
#             - video_title
#             - video_description
#             - channel_title
#             - channel_id
#             - publish_time
#             - time_created
#             - time updated
#     - On failure:
#         - returns the error
#     '''

#     # get the parameters and validate
#     try:
#         query = request.query_params.get('query')
#         number = int(request.query_params.get('number', 5))
#     except:
#         return Response({"message": "Invalid parameters"}, status=status.HTTP_400_BAD_REQUEST)

#     if number > 20 or number<=0:
#         return Response({"message": "Number should be between 1 and 20"}, status=status.HTTP_400_BAD_REQUEST)
    
#     # extract access token from header and get user
#     authorization_header = request.headers.get('Authorization')
#     access_token = authorization_header.split(' ')[1]
#     user = get_user_from_token(access_token)
    
#     # Search if any such query is associated with the user 
#     user_object_id = ObjectId(user._id)
#     if UserQuery.objects.raw({'query': query, 'user': user_object_id}).count()==0:
#         return Response({"message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)

#     try:
#         search_query = SearchQuery.objects.get({'query': query})
#     except:
#         return Response({"message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)

#     # return the data
#     data = {}
#     data['query'] = query
#     data['number'] = number
#     try:
#         search_query_videos = search_query.videos
#         num_videos = len(search_query_videos)
#         if number > num_videos:
#             data['message'] = f"Only {num_videos} video(s) found for this query"
#             number = num_videos
#         video_ids = [video._id for video in search_query_videos]
#         video_list = list(YTVideo.objects.raw({'_id': {'$in': video_ids}}).order_by([('publish_time', DESCENDING)]).limit(number))
#         serializer = VideoSerializer(video_list, many=True)
#         data['videos'] = serializer.data
#     except:
#         data['videos'] = []
#         data['message'] = "No video found"
#     return Response(data, status=status.HTTP_200_OK)


# @api_view(['GET'])
# def get_user_queries(request):
#     '''
#     View which returns all the queries associated with the user. Requires authentication
    
#     Request parameters:
#     None

#     Response:
#     - On success:
#         - queries: a list of strings denoting queries
#     - On failure
#         - returns the error
#     '''

#     # extract access token from header and get user
#     authorization_header = request.headers.get('Authorization')
#     access_token = authorization_header.split(' ')[1]
#     user = get_user_from_token(access_token)

#     # fetch all the queries associated with the current user
#     user_obj_id = ObjectId(user._id)
#     if UserQuery.objects.raw({'user': user_obj_id}).count()>0:
#         user_queries = [query.query for query in list(UserQuery.objects.raw({'user': user_obj_id}))]
#         return Response({"queries": user_queries}, status=status.HTTP_200_OK)
#     else:
#         return Response({"message": "No queries associated with the user"}, status=status.HTTP_204_NO_CONTENT)


# @api_view(['POST'])
# def delete_query(request):
#     '''
#     View which deletes the query for the current user. Requires authentication
    
#     Request parameters
#     - query(Required): query which is to be deleted

#     Response:
#     - On success:
#         - returns a message that query has been deleted
#     - On failure
#         - returns the error
#     '''

#     # extract the access token from the header and get user
#     authorization_header = request.headers.get('Authorization')
#     access_token = authorization_header.split(' ')[1]
#     user = get_user_from_token(access_token)
#     query = request.data.get('query', None)
#     if query == None:
#         return Response({"message": "query not found in parameters"}, status=status.HTTP_400_BAD_REQUEST)
#     elif len(query) == 0:
#         return Response({"message": "Invalid query"}, status=status.HTTP_400_BAD_REQUEST)

#     # delete the record if it exists or return the error
#     user_obj_id = ObjectId(user._id)
#     try:
#         user_query = UserQuery.objects.get({'user': user_obj_id, 'query': query})
#         user_query.delete()
#         return Response({"message": "Deleted query"}, status=status.HTTP_200_OK)
#     except:
#         return Response({"message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)

