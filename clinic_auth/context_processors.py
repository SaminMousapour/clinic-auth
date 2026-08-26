import os
from django.conf import settings
from allauth.socialaccount.models import SocialApp


def google_oauth(request):
    # Check database SocialApp
    try:
        db_app = SocialApp.objects.filter(provider='google').first()
        db_enabled = bool(db_app and db_app.client_id and db_app.secret)
    except Exception:
        db_enabled = False
    
    # Also check env vars
    env_enabled = bool(os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET'))
    
    # Also check settings (legacy)
    app = settings.SOCIALACCOUNT_PROVIDERS.get('google', {}).get('APP', {})
    settings_enabled = bool(app.get('client_id') and app.get('secret'))
    
    return {'google_enabled': db_enabled or settings_enabled or env_enabled}
