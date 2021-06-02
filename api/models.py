from api.search import Video
from pymodm import MongoModel, fields
from authentication.models import User
from pymongo import DESCENDING, IndexModel, ASCENDING


class YTVideo(MongoModel):
    video_id = fields.CharField(max_length=100)
    video_title = fields.CharField(max_length=200)
    video_description = fields.CharField(max_length=500, min_length=0)
    channel_title = fields.CharField(max_length=100)
    channel_id = fields.CharField(max_length=200)
    publish_time = fields.DateTimeField()
    time_created = fields.DateTimeField()
    time_updated = fields.DateTimeField() 


    def indexing(self):
        doc = Video(
            meta = {"id": self.video_id},
            title = self.video_title,
            publish_date = self.publish_time
        )
        # try:
        doc.save()
        return doc.to_dict(include_meta=True)
        # except Exception as e:
        #     print(e)
        #     return None

    class Meta:
        final = True
        indexed = [
            IndexModel([('video_id', ASCENDING)], unique=True)
        ]


class SearchQuery(MongoModel):
    query = fields.CharField(max_length=100)
    slug = fields.CharField(max_length=200)
    videos = fields.ListField(field=fields.ReferenceField(YTVideo, on_delete=fields.ReferenceField.DO_NOTHING), blank=True)
    time_created = fields.DateTimeField()
    time_updated = fields.DateTimeField()

    class Meta:
        final = True
        indexes = [
            IndexModel([('query', ASCENDING)], unique=True),
            IndexModel([('slug', ASCENDING)], unique=True),
        ]
    

    
class UserQuery(MongoModel):
    user = fields.ReferenceField(User, on_delete=fields.ReferenceField.CASCADE)
    query = fields.ReferenceField(SearchQuery, on_delete=fields.ReferenceField.CASCADE)
    time_created = fields.DateTimeField()
    last_accessed = fields.DateTimeField()
    times_accessed = fields.IntegerField()

    class Meta:
        final = True
        indexes = [
            IndexModel([('user', ASCENDING)]),
            IndexModel([('user', ASCENDING), ('query', ASCENDING)], unique=True),
        ]
