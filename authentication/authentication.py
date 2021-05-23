from rest_framework.authentication import BaseAuthentication
from cryptography.fernet import Fernet
from django.conf import settings
from authentication.models import User

class JWTAuthentication(BaseAuthentication):
    
    def authenticate(self, username=None, password=None,**kwargs):
        if username == None or password == None:
            return None
        try:
            user = User.objects.get({'username': username})
            fernet = Fernet(settings.PASSWORD_ENCRYPTION_KEY)
            password_bytes = bytes(user.password, "utf-8")
            decrypted_password = fernet.decrypt(password_bytes).decode()
            if decrypted_password == password:
                return user
            else:
                return None
        except User.DoesNotExist:
            return None