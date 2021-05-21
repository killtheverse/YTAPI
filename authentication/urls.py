from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from .views import login_view, logout_view, register_user

urlpatterns = [
    path('logout/', logout_view, name='logout'),
    path('login/', login_view, name='login'),
    path('login/refresh/', TokenRefreshView.as_view()),
    path('register/', register_user),
]
