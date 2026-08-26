from django.core.management.base import BaseCommand
from accounts.email_utils import send_doctor_patient_list_for_tomorrow


class Command(BaseCommand):
    help = 'Send doctor patient list for tomorrow\'s appointments (run in evening)'

    def handle(self, *args, **options):
        self.stdout.write('Sending doctor patient lists for tomorrow...')
        
        result = send_doctor_patient_list_for_tomorrow()
        
        if result['total'] == 0:
            self.stdout.write(
                self.style.WARNING('No doctors with appointments tomorrow')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Completed: {result["sent"]} sent, {result["failed"]} failed '
                    f'out of {result["total"]} doctors'
                )
            )
            
            if result['failed'] > 0:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send {result["failed"]} reminder(s)')
                )