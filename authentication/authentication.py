from django.contrib.auth import get_user_model
import jwt
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from django.conf import settings


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        User = get_user_model()
        authorization_header = request.headers.get('Authorization')
        if not authorization_header:
            return None
        try:
            access_token = authorization_header.split(' ')[1]
            payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Access Token expired')
        except IndexError:
            raise exceptions.AuthenticationFailed('Token prefix missing')
        except:
            raise exceptions.AuthenticationFailed('Invalid Header')
        user = User.objects.filter(id=payload['user_id']).first()
        if user is None:
            raise exceptions.AuthenticationFailed('User not found')

        return (user, None)