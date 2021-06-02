from os import stat
import bson
from elasticsearch_dsl.aggs import A
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
from .search import Video

from django.conf import settings
from .models import YTVideo
import requests

from elasticsearch_dsl.query import Q, Range, Match
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search


@api_view(['GET', 'POST'])
def query_list(request):
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

        last_fetched = offset + data["number"]
        if last_fetched >= total_docs:
            data["next"] = None

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
    
    return Response(data=data, status=status.HTTP_200_OK)
    

@api_view(['GET'])
def date_search(request):
    try:
        time_from = request.query_params.get("from", (datetime.now()-timedelta(days=10)))
        time_to = request.query_params.get("to", datetime.now())
    except:
        return Response({"message": "Bad request"}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(time_from, str):
        time_from_str = time_from
        try:
            time_from = datetime.strptime(time_from, "%Y-%m-%dT%H:%M:%SZ")
        except Exception as e:
            return Response({"message": e}, status=status.HTTP_400_BAD_REQUEST)
    else:
        time_from_str = None

    if isinstance(time_to, str):
        time_to_str = time_to
        try:
            time_to = datetime.strptime(time_to, "%Y-%m-%dT%H:%M:%SZ")
        except Exception as e:
            return Response({"message": e}, status=status.HTTP_400_BAD_REQUEST)
    else:
        time_to_str = None
    
    try:
        limit = int(request.query_params.get('limit', 5))
        offset = int(request.query_params.get('offset', 0))
    except:
        return Response({"message": "Invalid query parameters"}, status=status.HTTP_400_BAD_REQUEST)

    if offset<0 or limit<1:
        return Response({"message": "Offset should be >=0 and limit should be >=1"}, status=status.HTTP_400_BAD_REQUEST)

    client = Elasticsearch([settings.ELASTIC_SEARCH_URL])
    print(time_from, time_to)

    query_body = {
        "from": offset,
        "size": limit,
        "sort": [{
            "publish_date": {"order": "desc"}
        }],
        "query": {
            "range": {
                "publish_date": {
                    "gte": time_from,
                    "lte": time_to,
                }
            }
        }
    }
    s = Search(using=client, index='ytvideo', doc_type='video').from_dict(query_body)   
    response = s.execute()
    
    video_ids = []
    for hit in response:
        video_ids.append(hit.meta.id)
    
    

    videos = list(YTVideo.objects.raw({"video_id": {"$in": video_ids}}))
    serializer = VideoSerializer(videos, many=True)

    next = "127.0.0.1:8000/api/videos/search/date?limit="+str(limit)+"&offset="+str(limit+offset)
    if time_from_str != None:
        next += "&next="+time_from_str
    if time_to_str != None:
        next += "&to="+time_to_str

    if len(video_ids) == 0:
        next = None
    return Response(
        data={
            "next": next,
            "data": serializer.data
        }
    , status=status.HTTP_200_OK)


@api_view(['GET'])
def title_search(request):
    try:
        key = request.query_params.get("key", None)
    except:
        return Response({"message":"Provide a key"}, status=status.HTTP_400_BAD_REQUEST)
    if len(key) == 0:
        return Response({"messaeg": "Enter a valid key"}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        limit = int(request.query_params.get('limit', 5))
        offset = int(request.query_params.get('offset', 0))
    except:
        return Response({"message": "Invalid query parameters"}, status=status.HTTP_400_BAD_REQUEST)

    if offset<0 or limit<1:
        return Response({"message": "Offset should be >=0 and limit should be >=1"}, status=status.HTTP_400_BAD_REQUEST)
    
    client = Elasticsearch([settings.ELASTIC_SEARCH_URL])


    query_body = {
        "from": offset,
        "size": limit,
        "sort": [{
            "title.keyword": {"order": "asc"}
        }],
        "query": {
            "match": {
                "title": {
                    "query": key,
                }
            }
        }
    }
    s = Search(using=client, index='ytvideo', doc_type='video').from_dict(query_body)
    
    response = s.execute()
    video_ids = []
    for hit in response:
        video_ids.append(hit.meta.id)
    

    videos = list(YTVideo.objects.raw({"video_id": {"$in": video_ids}}))
    serializer = VideoSerializer(videos, many=True)

    next = "127.0.0.1:8000/api/videos/search/title?key=" + key+"&offset="+str(offset+limit)+"&limit="+str(limit)
    if len(video_ids) == 0:
        next = None
    return Response(
        data={
            "next": next,
            "data": serializer.data
        }
    , status=status.HTTP_200_OK)


@api_view(['GET'])
def number_search(request):
    client = Elasticsearch([settings.ELASTIC_SEARCH_URL])

    query_body = {
        "aggs": {
            "by_number": {
                "terms": {
                    "field": "number",
                    "order": {"_count": "desc"}
                },
                "aggs": {
                    "top_hit_three": {
                        "top_hits": {"size": 3}
                    }
                }
            }
        }
    }

    s = Search(using=client, index='ytvideo', doc_type='video').from_dict(query_body)
    response = s.execute()
    
    data = {
        "data": []
    }
    
    for item in response.aggregations.by_number.buckets:
        video_ids = []
        for hit in item.top_hit_three.hits.hits:
            video_ids.append(hit["_id"])
        videos = list(YTVideo.objects.raw({"video_id": {"$in": video_ids}}))
        serializer = VideoSerializer(videos, many=True)
        bucket = {
            "key": item.key,
            "doc_count": item.doc_count,
            "videos": serializer.data
        }
        data["data"].append(bucket)
    
    data["buckets"] = len(data["data"])
    return Response(data, status=status.HTTP_200_OK)


