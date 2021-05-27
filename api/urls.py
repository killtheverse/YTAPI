from django.urls import path
from .views import (
    bulk_fetch, bulk_register, query_list, query_detail
)

urlpatterns = [
    path('queries/', query_list),
    path('queries/<str:slug>/', query_detail),
    path('bulk_fetch/', bulk_fetch),
    path('bulk_register/', bulk_register),
]
