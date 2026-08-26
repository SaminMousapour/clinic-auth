import os
from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Create or update the Google SocialApp for OAuth'

    def handle(self, *args, **options):
        client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')

        if not client_id or not secret:
            self.stdout.write(self.style.WARNING('GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set in env'))
            return

        site = Site.objects.get(id=1)
        site.domain = 'web-production-34eea.up.railway.app'
        site.name = 'ClinicOS'
        site.save()

        app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': secret,
                'key': '',
            }
        )
        app.sites.add(site)

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} Google SocialApp (id={app.id})'))
