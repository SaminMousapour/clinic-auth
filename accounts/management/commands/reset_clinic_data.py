from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.models import (
    Appointment,
    Doctor,
    EmailLog,
    MedicalRecord,
    Medication,
    Patient,
    PatientRecord,
    PatientVisit,
    Prescription,
    HealthReading,
)


class Command(BaseCommand):
    help = ('Wipe all clinic data (patients, doctors, appointments, medications, '
            'readings, records) plus non-admin user accounts, then re-seed clean '
            'data with the current encryption key.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-reseed', action='store_true', help='Wipe data but do not re-seed.'
        )

    def handle(self, *args, **options):
        for model in (Prescription, MedicalRecord, PatientRecord, Appointment,
                      PatientVisit, HealthReading, Medication):
            model.objects.all().delete()

        for model in (Patient, Doctor):
            model.objects.all().delete()

        # Remove any leftover non-admin accounts (admin/staff accounts are kept).
        User = get_user_model()
        User.objects.filter(is_staff=False).delete()

        EmailLog.objects.all().delete()

        if options.get('no_reseed'):
            self.stdout.write(self.style.SUCCESS('Data wiped (no reseed).'))
            return

        call_command('seed_admin')
        call_command('seed_doctors')
        self.stdout.write(self.style.SUCCESS('Data wiped and re-seeded with current encryption key.'))