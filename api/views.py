import bson
from pymongo import DESCENDING
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import (
    SearchQuery
)
from .serializers import VideoSerializer
from django.utils import timezone
from authentication.utils import get_user_from_token
from .tasks import fetch_single_video
from .utils import slugify
from datetime import datetime, timedelta


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
            "number": len(queries),
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
                return Response({"message": "Query not found"}, status=status.HTTP_404_NOT_FOUND)
            if len(query)==0:
                return Response({"message":"Empty Query"}, status=status.HTTP_400_BAD_REQUEST)
            elif len(query)>100:
                return Response({"message":"Query length exceeded 100"}, status=status.HTTP_409_CONFLICT)
            
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
                    return Response({
                        "message": "Query already exists",
                        "query": search_query.query,
                        "slug": search_query.slug,
                        }, status=status.HTTP_200_OK)
                if search_query.time_updated < datetime.now()-timedelta(hours=1):
                    update_required = True
                else:
                    update_required = False
            except:
                update_required = True
                search_query = SearchQuery(
                    query = query,
                    users = [user],
                    time_created = timezone.now(),
                    slug = slugify(query),
                )
                search_query.save()

            # fetch the videos associated with this single query
            if update_required == True:
                fetch_single_video.delay(query)
            
            return Response({
                "message": "Query stored",
                "query": search_query.query,
                "slug": search_query.slug
                }, status=status.HTTP_201_CREATED)
        except:
            return Response({"message": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)
        


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


        qs = SearchQuery.objects.aggregate(
            {"$match": {"query": search_query.query}},
            {"$unwind": "$videos"},
            {"$lookup": {
                "from": "yt_video",
                "localField": "videos",
                "foreignField": "_id",
                "as": "videos"
            }},
            {"$unwind": "$videos"},
            {"$sort": {"videos.publish_time": DESCENDING}},
            {"$group": {"_id": "$query", "videos": {"$push": "$videos"}}},
            {"$project": {"videos": {"$slice": ["$videos", offset, limit]}}}
        )
        for query_data in qs:
            query = query_data["_id"]
            query_videos = query_data["videos"]
        
        serializer = VideoSerializer(query_videos, many=True)
        data = {
            "query": query,
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
            return Response({"User has not registered this query"}, status=status.HTTP_409_CONFLICT)


@api_view(["POST"])
def bulk_register(request):
    '''
    Register queries in bulk for the user. Requires authentication.

    Request parameters:
    - queries: a list consisting of comma seperated strings of queries

    Resonse:
    - On success:
        - message: message that queries have been stored
    _ On failure:
        - message: error message
    '''
    try:
        queries = request.data.get("queries")
    except:
        return Response({"message": "Queries not present"}, status=status.HTTP_404_NOT_FOUND)

    try:
        #extract the access token from the header and get user
        authorization_header = request.headers.get('Authorization')
        access_token = authorization_header.split(' ')[1]
        user = get_user_from_token(access_token)

        update_queries = [] 
        present_query_list = []
        present_queries = SearchQuery.objects.raw({"query": {"$in": queries}})
        for present_query in present_queries:
            present_query_list.append(present_query.query)
            if user not in present_query.users:
                present_query.users.append(user)
            if present_query.time_updated < datetime.now() - timedelta(hours=1):
                update_queries.append(present_query.query)
        
        new_queries = []
        for query in queries:
            if query not in present_query_list:
                search_query = SearchQuery(
                    query = query,
                    users = [user],
                    time_created = timezone.now(),
                    slug = slugify(query),
                )
                new_queries.append(search_query)
                update_queries.append(query)
        if len(new_queries) > 0:
            new_queries = SearchQuery.objects.bulk_create(new_queries)

        for query in update_queries:
            fetch_single_video.delay(query)

        return Response({"message": "Registered all queries"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"message": str(e)}, status=status.status.HTTP_400_BAD_REQUEST)


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
        limit = int(request.query_params.get('limit', 5))
        offset = int(request.query_params.get('offset', 0))
    except:
        return Response({"message": "Invalid query parameters"}, status=status.HTTP_400_BAD_REQUEST)

    if offset < 0 or offset >= 20:
        return Response({"message": "Offset should be between 0 and 19"}, status=status.HTTP_400_BAD_REQUEST)
    if limit < 1 or limit > 20:
        return Response({"message": "Limit should be between 1 and 20"}, status=status.HTTP_400_BAD_REQUEST)
    
    if offset+limit >= 20:
        limit = 20-offset
    
    try:
        queries = request.data.get("queries")
    except:
        return Response({"message": "Queries not present"}, status=status.HTTP_404_NOT_FOUND)

    try:
        search_queries = SearchQuery.objects.aggregate(
            {"$match": {"query": {"$in": queries}}},
            {"$unwind": "$videos"},
            {"$lookup": {
                "from": "yt_video",
                "localField": "videos",
                "foreignField": "_id",
                "as": "videos"
            }},
            {"$unwind": "$videos"},
            {"$sort": {"videos.publish_time": DESCENDING}},
            {"$group": {"_id": "$query", "videos": {"$push": "$videos"}}},
            {"$project": {"videos": {"$slice": ["$videos", offset, limit]}}}
        )

        data = {
            "limit": limit,
            "offset": offset,
            "data": [],
        }
        

        for search_query in search_queries:
            serializer = VideoSerializer(search_query["videos"], many=True)
            query_obj = {
                "query": search_query["_id"],
                "videos": serializer.data,
            } 
            data["data"].append(query_obj)
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
