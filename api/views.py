from os import stat
import bson
from pymongo import DESCENDING
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import (
    SearchQuery,
    UserQuery
)
from .serializers import VideoSerializer
from django.utils import timezone
from authentication.utils import get_user_from_token
from .tasks import fetch_single_video
from .utils import slugify
from datetime import datetime, timedelta

from django.conf import settings
from .models import YTVideo
import requests


@api_view(['GET', 'POST'])
def query_list(request):
    '''
    List all the queries of the user or create a new query. Requires authentication.

    if method == GET:
        Request parameters:
        None

        Response:
        - On success:
            - queries: a list of objects with keys:
                query: query string
                slug: slug which will be used to access the query
        - On failure
            - message: error message

    elif method == POST:
        Request parameters:
        - query: query which is to be searched

        Response:
        - On success
            - message: message that query has been stored/ it already exists
            - query: query registered
            - slug: slug to access the registered query
        - On failure
            - message: error message
    '''
    if request.method == "GET":
        try:
            limit = int(request.query_params.get('limit', 5))
            offset = int(request.query_params.get('offset', 0))
        except:
            return Response({"message": "Invalid query parameters"}, status=status.HTTP_400_BAD_REQUEST)

        if offset<0 or limit<1:
            return Response({"message": "Offset should be >=0 and limit should be >=1"}, status=status.HTTP_400_BAD_REQUEST)

        # extract access token from header and get user
        authorization_header = request.headers.get("Authorization")
        access_token = authorization_header.split(" ")[1]
        user = get_user_from_token(access_token)
        user_id = bson.ObjectId(user._id)
        
        user_queries = UserQuery.objects.aggregate(
            {"$facet": {
                "total": [
                    {"$match": {"user": user_id}},
                    {"$count": "total"}  
                ],
                "queries": [
                    {"$match": {"user": user_id}},
                    {"$lookup": {
                        "from": "search_query",
                        "localField": "query",
                        "foreignField": "_id",
                        "as": "search_query"
                    }},
                    {"$unwind": "$search_query"},
                    {"$sort": {"last_accessed": DESCENDING}},
                    {"$limit": limit+offset},
                    {"$skip": offset},
                    {"$unwind": "$search_query.videos"},
                    {"$lookup": {
                        "from": "yt_video",
                        "localField": "search_query.videos",
                        "foreignField": "_id",
                        "as": "search_query.videos"
                    }},
                    {"$unwind": "$search_query.videos"},
                    {"$sort": {"search_query.videos.publish_time": DESCENDING}},
                    {"$group": {
                        "_id": {
                            "query": "$search_query.query",
                            "slug": "$search_query.slug",
                            "times_accessed": "$times_accessed",
                            "last_accessed": "$last_accessed",
                            "time_created": "$time_created",
                        }, 
                        "videos": {"$push": "$search_query.videos"}},
                    },
                    {"$sort": {"_id.last_accessed": DESCENDING}}
                ]
            }}    
        )
        try:
            for uq in user_queries:
                total_docs = uq["total"][0]["total"]
                user_queries = uq["queries"]
        except:
            total_docs = 0
            user_queries = []
        queries = []
        for user_query in user_queries:
            serializer = VideoSerializer(user_query["videos"], many=True)
            queries.append({
                "query": user_query["_id"]["query"],
                "slug": user_query["_id"]["slug"],
                "times_accessed": user_query["_id"]["times_accessed"],
                "last_accessed": user_query["_id"]["last_accessed"],
                "time_created": user_query["_id"]["time_created"],
                "videos": serializer.data               
            })
        data = {
            "username": user.username,
            "limit": limit,
            "offset": offset,
            "next": "127.0.0.1:8000/api/queries/?limit="+str(limit)+"&offset="+(str(offset+limit)),
            "number": len(queries),
            "queries": queries,    
        }
        
        # queries = [query_obj["query"] for query_obj in data["queries"]]
        # search_queries = SearchQuery.objects.raw({"query": {"$in": queries}})
        # query_ids = [sq._id for sq in search_queries]
        # UserQuery.objects.raw({"user": user_id, "query": {"$in": query_ids}}).update({
        #     "$set": {
        #         "last_accessed": timezone.now()},
        #         "$inc": {"times_accessed": 1}
        # })

        last_fetched = offset + data["number"]
        if last_fetched >= total_docs:
            data["next"] = "No more queries"

        return Response(data=data, status=status.HTTP_200_OK)


    elif request.method == 'POST':
        
        # check if query is valid
        query = request.data.get("query", None)
        if query == None:
            return Response({"message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)
        if len(query)==0:
            return Response({"message": "Empty Query"}, status=status.HTTP_400_BAD_REQUEST)
        elif not isinstance(query, str):
            return Response({"message": "Enter a valid string"}, status=status.HTTP_400_BAD_REQUEST)
        elif len(query)>100:
            return Response({"message":"Query length exceeded 100"}, status=status.HTTP_409_CONFLICT)
        
        # extract access token from header and get user
        authorization_header = request.headers.get('Authorization')
        access_token = authorization_header.split(' ')[1]
        user = get_user_from_token(access_token)
        
        # check if user already has query with same name
        # if not, then create the query
        
        try:
            search_query = SearchQuery.objects.get({"query": query})
        except:
            search_query = SearchQuery(
                query = query,
                slug = slugify(query),
                time_created = timezone.now(),
            )
            search_query.save()
            fetch_single_video.delay(search_query.query)
            
        try:
            user_query = UserQuery.objects.get({"query": search_query._id, "user": user._id})
            return Response({
                "message": "Query already exists",
                "query": user_query.query.query,
                "slug": user_query.query.slug
            }, status=status.HTTP_200_OK)
        except:
            user_query = UserQuery.objects.create(
                query = search_query,
                user = user,
                time_created = timezone.now(),
                times_accessed = 0,
                last_accessed = timezone.now()
            )
            user_query.save()
        
        return Response({
            "message": "Query stored",
            "query": search_query.query,
            "slug": search_query.slug
            }, status=status.HTTP_201_CREATED)
        
        


@api_view(["GET", "DELETE"])
def query_detail(request, slug):
    '''
    Returns the videos associated with a query or unregisters the user for the query.
    Requires authentication.
    
    if method == GET:
        Request parameters(parameters should be present in url):
        - limit(default 5)
        - offset(default 0)

        Response:
        - On success:
            - query: query that was searched
            - limit
            - offset
            - videos: a list consisting of videos objects:
                - video_id
                - video_title
                - video_description
                - channel_title
                - channel_id
                - publish_time
                - time_created
                - time updated
        - On failure:
            - message: error message
    
    elif method == DELETE:
        Request parameters
        None

        Response:
        - On success:
            - message: a message that query has been deleted
        - On failure
            - message: error message
    '''
    if request.method == "GET":
        
        # extract access token from header and get user
        authorization_header = request.headers.get("Authorization")
        access_token = authorization_header.split(" ")[1]
        user = get_user_from_token(access_token)
        user_id = bson.ObjectId(user._id)

        try:
            search_query = SearchQuery.objects.get({"slug": slug})
        except:
            return Response({"message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)


        try:
            user_query = UserQuery.objects.get({"user": user_id, "query": search_query._id})
        except:
            return Response({"message": "Query not registered for user"}, status=status.HTTP_404_NOT_FOUND)


        video_ids = [video._id for video in search_query.videos]
        videos_qs = YTVideo.objects.aggregate(
            {"$match": {"_id": {"$in": video_ids}}},
            {"$sort": {"publish_time": DESCENDING}},
            {"$project": {"_id": 0}}
        )

        data = {
            "query": search_query.query,
            "slug": search_query.slug,
            "last_accessed": user_query.last_accessed,
            "times_accessed": user_query.times_accessed,
            "time_created": user_query.time_created,
            "videos": [video for video in videos_qs]
        }

        user_query.times_accessed += 1
        user_query.last_accessed = timezone.now()
        user_query.save()
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

        try:
            user_query = UserQuery.objects.get({"user": user._id, "query": search_query._id})
        except:
            return Response({"message": "Query not registered for the user"}, status=status.HTTP_409_CONFLICT)

        # delete the record if it exists else return the message
        user_query.delete()
        return Response({"message": "Query removed for user"}, status=status.HTTP_200_OK)
    


@api_view(['POST'])
def bulk_fetch(request):
    '''
    Fetches the results for queries in bulk. Requires authentication.

    Request parameters:
    - queries: a list of comma seperated strings of queries
    - limit(in url params)
    - offset(in url params)

    Response:
    - On success:
        - limit
        - offset
        - data: a list of objects:
            - query: query that was searched
            - videos: a list of video objects:
                - video_id
                - video_title
                - video_description
                - channel_title
                - channel_id
                - publish_time
                - time_created
                - time updated
    - On failure:
        - message: error message
    '''
    
    
    try:
        queries = request.data.get("queries")
    except:
        return Response({"message": "Queries not present in request"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        for query in queries:
            if not isinstance(query, str):
                return Response({"message": "Enter a valid list of strings"}, status=status.HTTP_400_BAD_REQUEST)
    except:
        return Response({"message": "Enter a valid list of strings"}, status=status.HTTP_400_BAD_REQUEST)

    # extract access token from header and get user
    authorization_header = request.headers.get("Authorization")
    access_token = authorization_header.split(" ")[1]
    user = get_user_from_token(access_token)
    user_id = bson.ObjectId(user._id)

        
    search_queries = SearchQuery.objects.raw({"query": {"$in": queries}})
    query_ids = [query._id for query in search_queries]

    user_queries = UserQuery.objects.aggregate(
        {"$match": {"user": user_id, "query": {"$in": query_ids}}},
        {"$lookup": {
            "from": "search_query",
            "localField": "query",
            "foreignField": "_id",
            "as": "search_query"
        }},
        {"$unwind": "$search_query"},
        {"$sort": {"last_accessed": DESCENDING}},
        {"$unwind": "$search_query.videos"},
        {"$lookup": {
            "from": "yt_video",
            "localField": "search_query.videos",
            "foreignField": "_id",
            "as": "search_query.videos"
        }},
        {"$unwind": "$search_query.videos"},
        {"$sort": {"search_query.videos.publish_time": DESCENDING}},
        {"$group": {
            "_id": {
                "query": "$search_query.query",
                "slug": "$search_query.slug",
                "times_accessed": "$times_accessed",
                "last_accessed": "$last_accessed",
                "time_created": "$time_created",
            }, 
            "videos": {"$push": "$search_query.videos"}},
        },    
    )

    queries = []
    for user_query in user_queries:
        serializer = VideoSerializer(user_query["videos"], many=True)
        queries.append({
            "query": user_query["_id"]["query"],
            "slug": user_query["_id"]["slug"],
            "times_accessed": user_query["_id"]["times_accessed"],
            "last_accessed": user_query["_id"]["last_accessed"],
            "time_created": user_query["_id"]["time_created"],
            "videos": serializer.data               
        })
    data = {
        "username": user.username,
        "number": len(queries),
        "queries": queries,    
    }
    
    
    # UserQuery.objects.raw({"user": user_id, "query": {"$in": query_ids}}).update({
    #     "$set": {
    #         "last_accessed": timezone.now()},
    #         "$inc": {"times_accessed": 1}
    # })
    return Response(data=data, status=status.HTTP_200_OK)
    

@api_view(['POST'])
def test(requset, query):
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
            "video_id": result["id"]["videoId"],
            "publish_time": datetime.strptime(result["snippet"]["publishTime"], "%Y-%m-%dT%H:%M:%SZ"),
            "channel_title": result["snippet"]["channelTitle"],
            "channel_id": result["snippet"]["channelId"],
            "video_title": result["snippet"]["title"],
            "video_description": result["snippet"]["description"]
        }


    # delete old videos in bulk
    
    # old_video_ids = []
    # for video in search_query.videos:
    #     print(video)
    #     if video.video_id not in video_keys:
    #         old_video_ids.append(video._id)
    
    # print(old_video_ids)
    # deleted = YTVideo.objects.raw({'_id': {"$in": old_video_ids}})
    # print(deleted.count())
    # number = deleted.delete()
    # print(number)

    video_objs = []    
    existing_videos = YTVideo.objects.raw({"video_id": {"$in": video_keys}})
    print("count:", existing_videos.count())
    existing_video_ids = []
    for existing_video in existing_videos:
        existing_video_ids.append(existing_video.video_id)
        serializer = VideoSerializer(existing_video, video_data[existing_video.video_id])
        if serializer.is_valid():
            video_obj = serializer.save()
            video_objs.append(video_obj)
        else:
            print(serializer.errors)
    
    print(len(existing_video_ids))
    
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
    
    print("new count", len(new_videos))

    if len(new_videos) > 0:
        new_videos = YTVideo.objects.bulk_create(new_videos)

    video_objs.extend(new_videos)
    search_query = SearchQuery.objects.get({'query': query})
    search_query.videos = video_objs
    search_query.time_updated = timezone.now()
    search_query.save()
    return Response({"OK"})