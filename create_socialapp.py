import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_auth.settings')
import django
django.setup()
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

# Delete any existing
SocialApp.objects.all().delete()

site = Site.objects.get(id=1)

app = SocialApp.objects.create(
    provider='google',
    name='Google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', ''),
    secret=os.environ.get('GOOGLE_CLIENT_SECRET', ''),
    key=''
)
app.sites.add(site)
print('Created SocialApp with id:', app.id)
print('Provider:', app.provider)
print('Client ID:', app.client_id[:30])