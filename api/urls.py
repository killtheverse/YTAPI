from django.urls import path
from .views import (
    bulk_fetch, query_list, query_detail, test
)

urlpatterns = [
    path('queries/', query_list),
    path('queries/<str:slug>/', query_detail),
    path('bulk_fetch/', bulk_fetch),
    path('test/<str:query>/', test),
]
