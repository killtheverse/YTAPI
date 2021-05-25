from django.urls import path
from .views import (
    register_query, get_query_results,
    get_user_queries, delete_query
)

urlpatterns = [
    path('register_query/', register_query),
    path('get_query_results/', get_query_results),  
    path('get_user_queries/', get_user_queries),
    path('delete_query/', delete_query),
]
