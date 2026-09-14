from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from accounts.views import protected_media
from .views import custom_500

handler500 = custom_500

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
] + [path(f'{settings.MEDIA_URL.strip("/")}/<path:path>', protected_media, name='protected_media')]
