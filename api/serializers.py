from authentication.views import get_user_from_token
from django.db import models
from django.db.models import fields
from rest_framework import serializers
from .models import SearchQuery, UserQuery, YTVideo
from authentication.views import get_user_from_token


class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = YTVideo
        fields = '__all__'

