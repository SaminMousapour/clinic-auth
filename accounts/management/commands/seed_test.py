from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Doctor, Patient, Appointment, Medication
from datetime import date, timedelta
from accounts.encryption import encrypt_data

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed test patient, doctor, appointment, and medication for Telegram bot testing'

    def handle(self, *args, **options):
        # Clean any existing test users
        User.objects.filter(username__in=['testpatient', 'testdoctor']).delete()
        Doctor.objects.filter(user__username='testdoctor').delete()
        Patient.objects.filter(user__username='testpatient').delete()

        # Create patient user
        patient_user = User.objects.create_user(
            username='testpatient',
            email='patient@test.com',
            password='TestPass123',
            role='patient',
        )
        patient = Patient.objects.create(
            user=patient_user,
            first_name_encrypted=encrypt_data('Ali'),
            last_name_encrypted=encrypt_data('Ahmadi'),
            age=35,
            phone_encrypted=encrypt_data('+989123456789'),
            email_encrypted=encrypt_data('patient@test.com'),
        )

        # Create doctor user
        doctor_user = User.objects.create_user(
            username='testdoctor',
            email='doctor@test.com',
            password='TestPass123',
            role='doctor',
        )
        doctor = Doctor.objects.create(
            user=doctor_user,
            name_encrypted=encrypt_data('Dr. Sara Mohammadi'),
            medical_number='1001',
            medical_id='1001',
            specialty='Cardiology',
            accepted_insurance='bimeh_salamat',
        )

        # Appointment for TOMORROW (so 10 PM batch picks it up)
        tomorrow = date.today() + timedelta(days=1)
        appt = Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            patient_name='Ali Ahmadi',
            patient_phone='+989123456789',
            reason='Routine checkup',
            day=tomorrow.day,
            month=tomorrow.month,
            year=tomorrow.year,
            hour=14,
            minute=30,
        )

        # Medication due in ~5 minutes from now
        from accounts.email_utils import _clinic_tz
        from datetime import datetime
        now = datetime.now(_clinic_tz())
        med_time = (now + timedelta(minutes=5)).strftime('%H:%M')
        med = Medication.objects.create(
            patient=patient,
            name='Aspirin',
            dosage='100mg',
            times_of_day=med_time,
            days_of_week=','.join(['monday','tuesday','wednesday','thursday','friday','saturday','sunday']),
            is_active=True,
        )

        self.stdout.write(self.style.SUCCESS(f'''
Created test data:
  Patient: testpatient / TestPass123 (phone +989123456789)
  Doctor: testdoctor / TestPass123
  Appointment: tomorrow {tomorrow} at 14:30 with Dr. Sara Mohammadi
  Medication: Aspirin 100mg at {med_time} (daily)

Next steps:
1. Login as patient at /login/ with testpatient / TestPass123
2. Click "Connect Telegram" on landing page -> opens bot -> link account
3. Login as doctor (separate browser) -> Connect Telegram
4. Wait for 10 PM batch (appointment reminder to patient, patient list to doctor)
5. Wait ~5 min for medication reminder

Bot username: @ClinicOS_LeaveMeBe_Bot
'''))