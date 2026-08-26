from django.core.management.base import BaseCommand
from accounts.email_utils import send_appointment_reminders_for_tomorrow


class Command(BaseCommand):
    help = 'Send appointment reminder emails for appointments scheduled for tomorrow'

    def handle(self, *args, **options):
        self.stdout.write('Sending appointment reminders for tomorrow...')
        
        result = send_appointment_reminders_for_tomorrow()
        
        if result['total'] == 0:
            self.stdout.write(
                self.style.WARNING(f'No appointments scheduled for {result["date"]}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Completed: {result["sent"]} sent, {result["failed"]} failed '
                    f'out of {result["total"]} appointments for {result["date"]}'
                )
            )
            
            if result['failed'] > 0:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send {result["failed"]} reminder(s)')
                )