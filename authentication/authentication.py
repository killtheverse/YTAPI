from django.contrib.auth import get_user_model
import jwt
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from django.conf import settings


class JWTAuthentication(BaseAuthentication):
    
    def authenticate(self, username=None, password=None,**kwargs):
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None