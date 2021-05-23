from django.http.response import JsonResponse
from django.conf import settings
from .models import BlackListedRefreshToken, BlackListedAccessToken
import jwt


AUTHORIZED_URLS = [
    'api/',
    'auth/logout/',
    'auth/update/',
    'auth/change_password/',
    'auth/delete_user/'
]


class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):
        path = request.path_info.lstrip('/')
        
        try:
            refresh_token = request.POST['refresh']
            if BlackListedRefreshToken.objects.raw({'token': refresh_token}).count()>0:
                return JsonResponse({'Message': 'Access denied'}, status=403, safe=False)
        except:
            pass


        login_required = False
        for url in AUTHORIZED_URLS:
            if path.startswith(url):
                login_required = True
        if login_required == True:
            authorization_header = request.headers.get('Authorization')
            if not authorization_header:
                return JsonResponse({'Message': 'Authorization header not present'}, status=403, safe=False)
            try:
                access_token = authorization_header.split(' ')[1]
                if BlackListedAccessToken.objects.raw({'token': access_token}).count()>0:
                    print("Token exists")
                    return JsonResponse({'Message': 'Login required'}, status=403, safe=False)
                payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
            
            except jwt.ExpiredSignatureError:
                return JsonResponse({'Message:': 'Access token expired'}, status=401, safe=False)
                
            except Exception as e:
                print(e)
                return JsonResponse({'Message': 'Access denied'}, status=403, safe=False)
        else:
            pass

        response = self.get_response(request)
        return response
