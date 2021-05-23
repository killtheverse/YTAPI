from django.urls import path
from .views import (
    greeter, post_query, get_query_results, update_videos
)

urlpatterns = [
    path('greet/', greeter),
    path('post_query/', post_query),
    path('get_query_results/', get_query_results),
    path('update/', update_videos),    
]
