from django.utils import timezone
from rest_framework import serializers
from .models import YTVideo


class VideoSerializer(serializers.Serializer):
    video_id = serializers.CharField()
    video_title = serializers.CharField()
    video_description = serializers.CharField(allow_blank=True)
    channel_title = serializers.CharField()
    channel_id = serializers.CharField()
    publish_time = serializers.DateTimeField()
    time_created = serializers.DateTimeField(required=False)
    time_updated = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if len(attrs['video_description']) == 0:
            attrs['video_description'] = '-'
        if len(attrs['video_title']) > 200:
            attrs['video_title'] = attrs['video_title'][:200]
        if len(attrs['video_description']) > 500:
            attrs['video_description'] = attrs['video_description'][:500]
        if len(attrs['channel_title']) > 200:
            attrs['channel_title'] = attrs['channel_title'][:200]
        return attrs
            

    def create(self, validated_data):
        video = YTVideo(
            video_id = validated_data['video_id'],
            video_title = validated_data['video_title'],
            video_description = validated_data['video_description'],
            channel_title = validated_data['channel_title'],
            channel_id = validated_data['channel_id'],
            publish_time = validated_data['publish_time'],
            time_created = timezone.now(),
            time_updated = timezone.now()
        )
        video.save()
        return video
    
    def update(self, instance, validated_data):
        instance.video_title = validated_data.get('video_title', instance.video_title)
        instance.video_description = validated_data.get('video_description', instance.video_description)
        instance.channel_title = validated_data.get('channel_title', instance.channel_title)
        instance.time_updated = timezone.now()
        return instance




        