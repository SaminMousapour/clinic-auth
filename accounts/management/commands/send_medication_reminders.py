from django.core.management.base import BaseCommand
from accounts.email_utils import send_medication_reminders_for_today


class Command(BaseCommand):
    help = 'Send medication reminder emails for medications scheduled for today'

    def handle(self, *args, **options):
        self.stdout.write('Sending medication reminders for today...')
        
        result = send_medication_reminders_for_today()
        
        if result['total'] == 0:
            self.stdout.write(
                self.style.WARNING(f'No medications scheduled for {result["date"]}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Completed: {result["sent"]} sent, {result["failed"]} failed '
                    f'out of {result["total"]} medications for {result["date"]}'
                )
            )
            
            if result['failed'] > 0:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send {result["failed"]} reminder(s)')
                )