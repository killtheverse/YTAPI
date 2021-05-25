from bson.objectid import ObjectId
from .models import User
from django.conf import settings
from bson import ObjectId
import jwt


def get_user_from_token(access_token):
    payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
    user = User.objects.get({'_id': ObjectId(payload['user_id'])})
    return user