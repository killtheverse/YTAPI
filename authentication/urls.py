from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from .views import (
    login_view, logout_view, register_user,
    update_user, change_password, delete_user

)
urlpatterns = [
    path('logout/', logout_view, name='logout'),
    path('login/', login_view, name='login'),
    path('login/refresh/', TokenRefreshView.as_view()),
    path('register/', register_user),
    path('update/', update_user),
    path('change_password/', change_password),
    path('delete_user/', delete_user),
]
