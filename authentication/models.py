from enum import unique
from django.db.models import indexes
from pymodm import MongoModel, fields
from django.conf import settings
from pymongo import IndexModel, ASCENDING


class User(MongoModel):
    username = fields.CharField(max_length=100)
    email = fields.EmailField()
    password = fields.CharField(max_length=300)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    account_created = fields.DateTimeField()
    account_modified = fields.DateTimeField()
    last_login = fields.DateTimeField()

    class Meta:
        indexes = [
            IndexModel([('username', ASCENDING)], unique=True),
        ]


class BlackListedAccessToken(MongoModel):
    token = fields.CharField(max_length=300)
    exp_time = fields.DateTimeField()

    class Meta:
        indexes = [
            IndexModel([('token', ASCENDING)], unique=True),
            IndexModel([('exp_time', ASCENDING)], expireAfterSeconds=330),
        ]


class BlackListedRefreshToken(MongoModel):
    token = fields.CharField(max_length=500)
    exp_time = fields.DateTimeField()

    class Meta:
        indexes = [
            IndexModel([('token', ASCENDING)], unique=True),
            IndexModel([('exp_time', ASCENDING)], expireAfterSeconds=864030),
        ]
