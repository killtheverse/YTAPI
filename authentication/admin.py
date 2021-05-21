from django.contrib import admin
from .models import BlackListedRefreshToken, BlacklistedAccessToken

admin.site.register(BlacklistedAccessToken)
admin.site.register(BlackListedRefreshToken)
