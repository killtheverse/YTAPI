from django.contrib import admin
from .models import SearchQuery, UserQuery, YTVideo
# Register your models here.

admin.site.register(SearchQuery)
admin.site.register(UserQuery)
admin.site.register(YTVideo)