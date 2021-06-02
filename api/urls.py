from django.urls import path
from .views import (
    bulk_fetch, date_search, number_search, 
    query_list, query_detail, title_search
)

urlpatterns = [
    path('queries/', query_list),
    path('queries/<str:slug>/', query_detail),
    path('bulk_fetch/', bulk_fetch),
    path('videos/search/title', title_search),
    path('videos/search/date', date_search),
    path('videos/search/number', number_search),
]
