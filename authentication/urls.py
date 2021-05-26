from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    user_view, register_user, login_view, logout_view,
    change_password
)
urlpatterns = [
    path('users/<str:username>/', user_view),
    path('logout/', logout_view),
    path('login/', login_view),
    path('login/refresh/', TokenRefreshView.as_view()),
    path('register/', register_user),
    path('change_password/', change_password),
]
