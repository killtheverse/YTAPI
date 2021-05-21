# from django.db import models
from djongo import models

class BlacklistedAccessToken(models.Model):
    token = models.CharField(max_length=300)
    exp_date = models.DateTimeField(auto_now_add=True)


class BlackListedRefreshToken(models.Model):
    token = models.CharField(max_length=500)
    exp_date = models.DateTimeField(auto_now_add=True)