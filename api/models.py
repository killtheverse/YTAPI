from pymodm import MongoModel, fields
from authentication.models import User
from pymongo import IndexModel, ASCENDING


class YTVideo(MongoModel):
    video_id = fields.CharField(max_length=100)
    video_title = fields.CharField(max_length=200)
    video_description = fields.CharField(max_length=500, min_length=0)
    channel_title = fields.CharField(max_length=100)
    channel_id = fields.CharField(max_length=200)
    publish_time = fields.DateTimeField()
    time_created = fields.DateTimeField()
    time_updated = fields.DateTimeField() 

    class Meta:
        final = True



class SearchQuery(MongoModel):
    query = fields.CharField(max_length=100)
    slug = fields.CharField(max_length=200)
    users = fields.ListField(field=fields.ReferenceField(User, on_delete=fields.ReferenceField.DO_NOTHING), blank=True)
    videos = fields.ListField(field=fields.ReferenceField(YTVideo, on_delete=fields.ReferenceField.DO_NOTHING), blank=True)
    time_created = fields.DateTimeField()
    time_updated = fields.DateTimeField()

    class Meta:
        final = True
        indexes = [
            IndexModel([('query', ASCENDING)], unique=True)
        ]
    

    
# class UserQuery(MongoModel):
#     user = fields.ReferenceField(User, on_delete=fields.ReferenceField.CASCADE)
#     query = fields.ReferenceField(YTVideo, on_delete=fields.ReferenceField.CASCADE)
#     time_created = fields.DateTimeField()

#     class Meta:
#         final = True
#         indexes = [
#             IndexModel([('user', ASCENDING)]),
#             IndexModel([('user', ASCENDING), ('user', ASCENDING)]),
#         ]


    




