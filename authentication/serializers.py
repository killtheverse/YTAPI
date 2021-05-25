from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from .validators import CustomPasswordValidator, CustomUsernameValidator
from .utils import get_user_from_token

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

        if len(username) > 100:
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
        
        error = CustomPasswordValidator().validate(attrs['password'])
        if error != None:
            raise serializers.ValidationError({'password': error})

        error = CustomUsernameValidator().validate(attrs['username'])
        if error != None:
            raise serializers.ValidationError({'username': error})

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
            account_modified = timezone.now(),
        )
        user.save()
        return user
    

class UpdateUserSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    def validate(self, attrs):
        if attrs.get('email', None) != None:
            if User.objects.raw({'email': attrs['email']}).count()>0:
                raise serializers.ValidationError({"email": "Email is already associated with an account"})
        if attrs.get('username', None) != None:
            error = CustomUsernameValidator().validate(attrs['username'])
            if error != None:
                raise serializers.ValidationError({'username': error})
                
            if User.objects.raw({'username': attrs['username']}).count()>0:
                raise serializers.ValidationError({"username": "Username is already associated with an account"})
        
        if attrs.get('first_name', None) != None:
            if len(attrs.get('first_name', None))==0 or len(attrs.get('first_name', None))>100:
                raise serializers.ValidationError({"first_name": "First name too long"})
        
        if attrs.get('last_name', None) != None:
            if len(attrs.get('last_name', None))==0 or len(attrs.get('last_name', None))>100:
                raise serializers.ValidationError({"last_name": "Last name too long"})
        return attrs

    
    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.username = validated_data.get('username', instance.username)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.account_modified = timezone.now()
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password1 = serializers.CharField(write_only=True, required=True)
    new_password2 = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        
        access_token = self.context.get('access_token')
        user = get_user_from_token(access_token)
        fernet = Fernet(settings.PASSWORD_ENCRYPTION_KEY)
        password_bytes = bytes(user.password, "utf-8")
        decrypted_password = fernet.decrypt(password_bytes).decode()
        if decrypted_password != attrs['old_password']:
            raise serializers.ValidationError({"old_password": "Incorrect password"})

        error = CustomPasswordValidator().validate(attrs['new_password1'])
        if error != None:
            raise serializers.ValidationError({"new_password1": error})

        if attrs['new_password1'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password2": "Passwords don't match"})
        
        if attrs['new_password1'] == attrs['old_password']:
            raise serializers.ValidationError({'new_password1': "New password can't be same as old password"})
    
        fernet = Fernet(settings.PASSWORD_ENCRYPTION_KEY)
        encrypted_password = fernet.encrypt(attrs['new_password1'].encode())
        attrs['new_password1'] = encrypted_password.decode("utf-8")
        return attrs

    def update(self, instance, validated_data):
        instance.password = validated_data['new_password1']
        instance.save()
        return instance
