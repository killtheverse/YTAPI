from django.urls import path
from .views import (
    greeter,
)

urlpatterns = [
    path('greet/', greeter)    
]
