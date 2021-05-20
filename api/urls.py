from django.urls import path
from .views import (
    greeter, hello
)

urlpatterns = [
    path('greet/', greeter),
    path('hello/', hello)    
]
