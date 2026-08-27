import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_auth.settings')
application = get_wsgi_application()

# Start the background email scheduler with the web process.
if os.environ.get('EMAIL_SCHEDULER_ENABLED', '1').strip().lower() in ('1', 'true', 'yes', 'on'):
    try:
        from clinic_auth.email_scheduler import start_email_scheduler
        start_email_scheduler()
    except Exception:
        import logging
        logging.getLogger('accounts').exception('Failed to start email scheduler')
