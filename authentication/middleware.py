from django.http.response import JsonResponse
from django.conf import settings
from rest_framework.response import Response
from .models import BlackListedRefreshToken, BlackListedAccessToken
from .utils import get_user_from_token
from django.conf import settings
import jwt
import json


class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):
        path = request.path_info.lstrip('/')
        
        try:
            json_request = json.loads(request.body)
            refresh_token = json_request.get('refresh')
            BlackListedRefreshToken.objects.get({'token': refresh_token})
            return JsonResponse({"message": "Login required"}, status=401, safe=False)
        except:
            pass


        login_required = False
        for url in settings.AUTHORIZED_URLS:
            if path.startswith(url):
                login_required = True
        if login_required == True:
            authorization_header = request.headers.get('Authorization')
            if not authorization_header:
                return JsonResponse({'message': 'Authorization header not present'}, status=401, safe=False)
            try:
                access_token = authorization_header.split(' ')[1]
                user = get_user_from_token(access_token)
                
                try:
                    BlackListedAccessToken.objects.get({'token': access_token})
                    return JsonResponse({'message': 'Login required'}, status=401, safe=False)
                except:
                    pass
                payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
            
            except jwt.ExpiredSignatureError:
                return JsonResponse({'message:': 'Access token expired'}, status=401, safe=False)
                
            except Exception as e:
                print(e)
                return JsonResponse({'message': 'Access denied'}, status=403, safe=False)
        else:
            pass

        response = self.get_response(request)
        return response
