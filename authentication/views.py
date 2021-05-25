from datetime import datetime
from authentication.serializers import LoginSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .authentication import JWTAuthentication
from django.http import JsonResponse
from .models import BlackListedAccessToken, BlackListedRefreshToken
from .serializers import RegisterUserSerializer, UpdateUserSerializer, ChangePasswordSerializer
from bson.objectid import ObjectId
from django.conf import settings
from django.utils import timezone
from .models import User
from api.models import UserQuery
from .utils import get_user_from_token


@api_view(['POST'])
def login_view(request):
    '''
    View for user login. Does not require authentication.
    
    Request parameters:
    - username: username of the user(Required)
    - password: password of the user(Required)

    Response:
    - On success:
        - username: username of the user logged in
        - tokens: a dictionary with 2 keys:
            - refresh: a reshresh token with a life time of 10 days
            - access: an access token with a life time of 5 minutes
    - On failure:
        - Returns the error
    '''

    # validate the data and generate token
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        pass
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # authenticate user
    username = request.POST['username']
    password = request.POST['password']
    user = JWTAuthentication.authenticate(request, username=username, password=password)
    if user == None:
        return Response({"message": "Invalid credentials"}, status=status.HTTP_403_FORBIDDEN)
    user.last_login = datetime.now()
    user.save()
    return Response(serializer.data, status=status.HTTP_200_OK)
    

@api_view(['POST'])
def logout_view(request):
    '''
    View which logs out the user which is currently logged in. Requires authentication.

    Request parameters:
    - refresh: The refresh token associated with the current user session(Required)

    Response:
    - On success:
        - Returns a message that user has logged out
    - On failure:
        - Returns the error
    '''

    # extract the access token from header
    authorization_header = request.headers.get('Authorization')
    if not authorization_header:
        return JsonResponse({'message': 'Authorization header not present'}, status=403, safe=False)
    try:
        access_token = authorization_header.split(' ')[1]
    except:
        return Response({"message": "Invalid access token"}, status=status.HTTP_400_BAD_REQUEST)


    # Blacklist access and refresh token
    try:
        blacklist_access_token = BlackListedAccessToken(
            token=access_token,
            exp_time=timezone.now()
        )
        blacklist_access_token.save()
        
        refresh_token = request.POST['refresh']
        blacklist_refresh_token = BlackListedRefreshToken(
            token=refresh_token,
            exp_time=timezone.now()
        )
        blacklist_refresh_token.save()

    except:
        return Response({"message": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"message": "Logged out"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def register_user(request):
    '''
    View which registers a user. Does not require authentication

    Request parameters(all required):
    - username
    - first_name
    - last_name
    - email
    - password: Password for the account
    - password2: Re-type password
    
    Response:
    - On success:
        - email: email of the user registered
        - username: username of the user registered
        - first_name: first name of the user registered
        - last name: last name of the user registered
    
    - On failure:
        - Returns the error
    '''

    serializer = RegisterUserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def update_user(request):
    '''
    View which updates user information. Required authentication

    Request parameters(Only provide those fields which need to be updated)
    - username
    - first_name
    - last_name
    - email

    Response
    - On success, post update fields of:
        - username
        - first_name
        - last_name
        - email

    - On failure
        - Returns the error
    '''

    # extract the access token from header and get the user
    authorization_header = request.headers.get('Authorization')
    access_token = authorization_header.split(' ')[1]
    user = get_user_from_token(access_token)
    
    # update the user data or return error
    serializer = UpdateUserSerializer(user, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def change_password(request):
    '''
    View which changes the password of the user

    Request parameters(all required)
    - old_password: current password of the user
    - new_password1: new password of the user
    - new_password2: Retype new password

    Returns
    - On success
        - Returns a message that the new password has been changed
    - On failure
        - Returns the error
    '''

    # extract access token from header and get user
    authorization_header = request.headers.get('Authorization')
    access_token = authorization_header.split(' ')[1]
    user = get_user_from_token(access_token)
    context = {"access_token": access_token}

    # change the password or return errors
    serializer = ChangePasswordSerializer(user, data=request.data, context=context)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Changed password"}, status=status.HTTP_200_OK)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def delete_user(request):
    '''
    View which deletes the user account. Requires authentication
    
    Request parameters
    - refresh: refresh token associated with the current user session(Required)

    Response
    - On success:
        - returns a message that user has been removed
    - On failure:
        - returns the error
    '''

    # extract access token from the header and get user
    authorization_header = request.headers.get('Authorization')
    access_token = authorization_header.split(' ')[1]
    user = get_user_from_token(access_token)

    # delete every query associated with the user
    user_obj_id = ObjectId(user._id)
    if UserQuery.objects.raw({'user': user_obj_id}).count()>0:
        user_queries = UserQuery.objects.raw({'user': user_obj_id})
        for query in user_queries:
            query.delete()

    # delete the user 
    user.delete()
    
    # blacklist the current access and refresh token
    try:
        blacklist_access_token = BlackListedAccessToken(
            token=access_token,
            exp_time=timezone.now()
        )
        blacklist_access_token.save()
        
        refresh_token = request.POST['refresh']
        blacklist_refresh_token = BlackListedRefreshToken(
            token=refresh_token,
            exp_time=timezone.now()
        )
        blacklist_refresh_token.save()

    except:
        return Response({"message": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"message": "User deleted"}, status=status.HTTP_204_NO_CONTENT)
