# from django.db import models
from djongo import models
from django.contrib.auth import get_user_model

class YTVideo(models.Model):
    video_id = models.CharField(max_length=100, primary_key=True)
    channel_title = models.CharField(max_length=100)
    video_title = models.CharField(max_length=200)
    video_description = models.TextField(max_length=500)
    publish_time = models.DateTimeField()


class SearchQuery(models.Model):
    query = models.CharField(max_length=100)
    video = models.ManyToManyField(YTVideo)
    time_created = models.DateTimeField(auto_now_add=True)
    time_updated = models.DateTimeField(auto_now=True)
    

class UserQuery(models.Model):
    User = get_user_model()
    user = models.ForeignKey(User, related_name='user_query', on_delete=models.CASCADE)
    query = models.CharField(max_length=100)
    time_created = models.DateTimeField(auto_now_add=True)
    




