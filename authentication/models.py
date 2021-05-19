from django.db import models


class JWTAccessToken(models.Model):
    token = models.CharField(max_length=300)
    exp_date = models.DateTimeField(auto_now_add=True)