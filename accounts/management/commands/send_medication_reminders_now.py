from django.core.management.base import BaseCommand
from accounts.email_utils import send_medication_reminders_for_current_time
from datetime import datetime


class Command(BaseCommand):
    help = 'Send medication reminder emails for medications due at the current time (run every 15 minutes)'

    def handle(self, *args, **options):
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        self.stdout.write(f'Sending medication reminders for current time ({time_str})...')
        
        result = send_medication_reminders_for_current_time()
        
        if result['total'] == 0:
            self.stdout.write(
                self.style.WARNING(f'No medications due at this time')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Completed: {result["sent"]} sent, {result["failed"]} failed '
                    f'out of {result["total"]} medications'
                )
            )
            
            if result['failed'] > 0:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send {result["failed"]} reminder(s)')
                )