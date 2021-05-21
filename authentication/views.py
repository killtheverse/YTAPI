import jwt
from authentication.serializers import LoginSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import authentication, serializers, status
from .authentication import JWTAuthentication
from django.http import JsonResponse
from .models import BlacklistedAccessToken, BlackListedRefreshToken
from .serializers import RegisterUserSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.conf import settings


@api_view(['POST'])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    username = request.POST['username']
    password = request.POST['password']
    user = JWTAuthentication.authenticate(request, username=username, password=password)
    if user == None:
        return Response({"Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(serializer.data, status=status.HTTP_200_OK)
    


@api_view(['POST'])
def logout_view(request):

    authorization_header = request.headers.get('Authorization')
    if not authorization_header:
        return JsonResponse({'Message': 'Authorization header not present'}, status=403, safe=False)
    try:
        access_token = authorization_header.split(' ')[1]
    except:
        return Response({"Message": "Invalid access token"}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        BlacklistedAccessToken.objects.create(token=access_token)
        refresh_token = request.POST['refresh']
        BlackListedRefreshToken.objects.create(token=refresh_token)
    except Exception as e:
        print("Exception:", e)
        return Response({"Message": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"Message": "Logged out"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def register_user(request):
    serializer = RegisterUserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"Message": "Created user"}, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



def get_user_from_token(access_token):
    payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
    User = get_user_model()
    user = User.objects.filter(id=payload['user_id']).first()
    return user
    

