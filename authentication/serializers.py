from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib import auth
from .authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from .models import JWTAccessToken


class LoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=100, write_only=True)
    tokens = serializers.SerializerMethodField()

    def get_tokens(self, obj):
        user = User.objects.get(username=obj['username'])
        token = RefreshToken.for_user(user)
        refresh_token = str(token)
        access_token = str(token.access_token)
        return {
            'refresh': refresh_token,
            'access': access_token,
        }

    class Meta:
        model = User
        fields = ['username', 'password', 'tokens']
    
    def validate(self, attrs):
        username = attrs.get('username', None)
        password = attrs.get('password', None)

        if username is None:
            raise serializers.ValidationError("Username is required to login")
        
        if password is None:
            raise serializers.ValidationError("A password is required to login")

        return {
            'username': username,
            'tokens': attrs.get('tokens'),
        }


