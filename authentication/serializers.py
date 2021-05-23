from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    tokens = serializers.SerializerMethodField()

    def get_tokens(self, obj):
        if User.objects.raw({'username': obj['username']}).count() == 0:
            raise serializers.ValidationError({"username": "username is not associated with any account"})
        user = User.objects.get({'username': obj['username']})
        token = RefreshToken.for_user(user)
        refresh_token = str(token)
        access_token = str(token.access_token)
        return {
            'refresh': refresh_token,
            'access': access_token,
        }

    def validate(self, attrs):
        username = attrs.get('username', None)

        if len(username) == 0:
            raise serializers.ValidationError({"username": "Enter valid username"})
        elif len(username) > 100:
            raise serializers.ValidationError({"username": "username too long (max length = 100)"})

        return {
            'username': username,
            'tokens': attrs.get('tokens'),
        }


class RegisterUserSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)
    username = serializers.CharField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    def validate(self, attrs):
        
        if User.objects.raw({'email': attrs['email']}).count()>0:
            raise serializers.ValidationError({"email": "Email is already associated with an account"})
        
        if User.objects.raw({'username': attrs['username']}).count()>0:
            raise serializers.ValidationError({"username": "Username is already associated with an account"})
        
        if attrs['password']!=attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match"})

        fernet = Fernet(settings.PASSWORD_ENCRYPTION_KEY)
        encrypted_password = fernet.encrypt(attrs['password'].encode())
        attrs['password'] = encrypted_password.decode("utf-8")
        
        return attrs

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
            account_created = timezone.now(),
        )
        user.save()
        return user
    