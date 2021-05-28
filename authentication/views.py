from api.models import SearchQuery, UserQuery
from datetime import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .authentication import JWTAuthentication
from .models import BlackListedAccessToken, BlackListedRefreshToken
from .serializers import RegisterUserSerializer, UpdateUserSerializer, ChangePasswordSerializer
from django.utils import timezone
from .models import User
from .utils import get_user_from_token
from rest_framework_simplejwt.tokens import RefreshToken


@api_view(['PATCH', 'DELETE'])
def user_view(request, username):
    '''
    Update or delete user. Requires authentication.
    
    if method == PATCH:

        Request parameters(atleast 1 required):
        - username: new username
        - email: new email
        - first_name: new first name
        - last_name: new last name

        Response:
        - On success:
            - username: new username
            - email: new email
            - first_name: new first name
            - last_name: new last name
        - On failure:
            - errors 
    
    elif method == DELETE:

        Request parameters:
        None

        Response:
        - On success:
            - message: message that user has been deleted
        - On failure:
            - message: error message
    '''
    
    if request.method == "PATCH":

        try:
            user = User.objects.get({"username": username})
        except:
            return Response({"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        authorization_header = request.headers.get("Authorization")
        access_token = authorization_header.split(" ")[1]
        if user != get_user_from_token(access_token):
            return Response({"message": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        # update the user data or return error
        serializer = UpdateUserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == "DELETE":
        
        try:
            user = User.objects.get({"username": username})
        except:
            return Response({"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)

        authorization_header = request.headers.get("Authorization")
        access_token = authorization_header.split(" ")[1]
        if user != get_user_from_token(access_token):
            return Response({"message": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

        # search_queries = SearchQuery.objects.raw({"users": user._id})
        # for query in search_queries:
        #     query.users.remove(user)
        #     query.save()
        
        # delete the user 
        user.delete()
        
        # blacklist the current access and refresh token
        try:
            blacklist_access_token = BlackListedAccessToken(
                token=access_token,
                exp_time=timezone.now()
            )
            blacklist_access_token.save()
            
            refresh_token = request.data.get("refresh")
            blacklist_refresh_token = BlackListedRefreshToken(
                token=refresh_token,
                exp_time=timezone.now()
            )
            blacklist_refresh_token.save()

        except:
            return Response({"message": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "User deleted"}, status=status.HTTP_200_OK)

    


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

    username = request.data.get("username", None)
    password = request.data.get("password", None)
    
    if username == None or password == None:
        return Response({"message": "Credentials not provided"}, status=status.HTTP_400_BAD_REQUEST)

    user = JWTAuthentication.authenticate(request, username=username, password=password)
    if user == None:
        return Response({"message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    user.last_login = datetime.now()
    user.save()
    token = RefreshToken.for_user(user)

    return Response({
        "username": user.username,
        "access": str(token.access_token),
        "refresh": str(token)
    }, status=status.HTTP_200_OK)
    

@api_view(['POST'])
def logout_view(request):
    '''
    Logs out the current user. Requires authentication.

    Request parameters:
    - refresh: The refresh token associated with the current user session(Required)

    Response:
    - On success:
        - message: message that user has logged out
    - On failure:
        - message: error message
    '''

    # extract the access token from header
    authorization_header = request.headers.get("Authorization")
    access_token = authorization_header.split(' ')[1]

    # Blacklist access and refresh token
    try:
        blacklist_access_token = BlackListedAccessToken(
            token=access_token,
            exp_time=timezone.now()
        )
        blacklist_access_token.save()
        
        refresh_token = request.data.get("refresh")
        blacklist_refresh_token = BlackListedRefreshToken(
            token=refresh_token,
            exp_time=timezone.now()
        )
        blacklist_refresh_token.save()

    except Exception as e:
        print(e)
        return Response({"message": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"message": "Logged out"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def register_user(request):
    '''
    Register a user. Does not require authentication

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
        - message: error message
    '''

    serializer = RegisterUserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def change_password(request):
    '''
    Changes the password of the user. Requires authentication

    Request parameters(all required)
    - old_password: current password of the user
    - new_password1: new password of the user
    - new_password2: Retype new password

    Returns
    - On success
        - message: message that the new password has been changed
    - On failure
        - messaeg: error message
    '''

    # extract access token from header and get user
    authorization_header = request.headers.get("Authorization")
    access_token = authorization_header.split(" ")[1]
    user = get_user_from_token(access_token)
    context = {"access_token": access_token}

    # change the password or return errors
    serializer = ChangePasswordSerializer(user, data=request.data, context=context)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Changed password"}, status=status.HTTP_200_OK)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

