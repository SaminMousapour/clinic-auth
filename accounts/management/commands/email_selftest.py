from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import datetime, date, timedelta, time as dt_time

from accounts.email_utils import (
    send_medication_reminders_for_current_time,
    send_appointment_reminders_due,
    send_doctor_patient_lists_due,
    _clinic_now, _clinic_today, _already_sent, _mark_sent,
)
from django.contrib.auth.models import User

from accounts.models import Patient, Medication, Appointment, Doctor, EmailLog

TEST_PATIENT_EMAIL = 'samin.mousapourgorji@gmail.com'
WEEKDAY_MAP = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


class Command(BaseCommand):
    help = 'One-shot: seed a test appointment (tomorrow now) + medication (now) and force-send all reminder emails.'

    def handle(self, *args, **options):
        self.stdout.write('Running email self-test...')

        # Never let a failure here take down the web process or fail the deploy.
        try:
            if _already_sent('selftest-done'):
                self.stdout.write('Self-test already ran; skipping.')
                return
            with transaction.atomic():
                r1, r2, r3 = self._seed_and_send()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Email self-test raised unexpectedly: {e}. '
                                               'The web process will continue normally.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Medication reminders: {r1}'))
        self.stdout.write(self.style.SUCCESS(f'Appointment reminders (24h-before): {r2}'))
        self.stdout.write(self.style.SUCCESS(f'Doctor patient lists: {r3}'))

        if r1.get('sent', 0) > 0 and r2.get('sent', 0) > 0 and r3.get('sent', 0) > 0:
            _mark_sent('selftest-done')
            self.stdout.write(self.style.SUCCESS('Email self-test complete — all senders delivered.'))
        else:
            self.stdout.write(self.style.ERROR('Email self-test had failures; it will be retried on next deploy.'))

    def _seed_and_send(self):
        patient = next((p for p in Patient.objects.all() if p.email == TEST_PATIENT_EMAIL), None)
        if not patient:
            self.stdout.write(self.style.WARNING(f'Patient {TEST_PATIENT_EMAIL} not found; creating a test patient.'))
            username_base = TEST_PATIENT_EMAIL.split('@')[0]
            username = username_base
            i = 1
            while User.objects.filter(username=username).exists():
                username = f'{username_base}{i}'
                i += 1
            user = User.objects.create(username=username)
            patient = Patient(
                user=user,
                age=30,
                first_name='Test',
                last_name='Patient',
                phone='00000000000',
                email=TEST_PATIENT_EMAIL,
                password_hash='',
            )
            patient.save()
            self.stdout.write(f'Created test patient #{patient.id} ({username}).')

        now = _clinic_now()
        today_name = WEEKDAY_MAP[now.weekday()]

        # ---- 1. Medication due ~2 minutes from now, today ----
        med_time = (now + timedelta(minutes=2)).time().strftime('%H:%M')
        med = next((m for m in Medication.objects.filter(patient=patient) if m.name == 'Email Test Med'), None)
        if med:
            med.time = dt_time(*(int(x) for x in med_time.split(':')))
            med.times_of_day = med_time
            med.days_of_week = today_name
            med.save()
            self.stdout.write(f'Updated test medication #{med.id} for today {med_time} ({today_name}).')
        else:
            med = Medication(
                patient=patient,
                time=dt_time(*(int(x) for x in med_time.split(':'))),
                times_of_day=med_time,
                times_per_day=1,
                days_of_week=today_name,
                hour=int(med_time.split(':')[0]),
                day=now.day,
                month=now.month,
                year=now.year,
            )
            med.name = 'Email Test Med'
            med.dosage = '1 tablet'
            med.save()
            self.stdout.write(f'Created test medication #{med.id} for today {med_time} ({today_name}).')

        # ---- 2. Appointment tomorrow at the current hour ----
        tomorrow = _clinic_today() + timedelta(days=1)
        appt = Appointment.objects.filter(
            patient=patient, day=tomorrow.day, month=tomorrow.month, year=tomorrow.year, is_cancelled=False
        ).first()
        if not appt:
            doctor = Doctor.objects.select_related('user').first()
            if not doctor:
                self.stdout.write(self.style.ERROR('No doctors available. Aborting.'))
                return None, None, None
            # Make sure the doctor can receive email for the test.
            if not doctor.user.email:
                doctor.user.email = TEST_PATIENT_EMAIL
                doctor.user.save()
                self.stdout.write(f'Assigned test email to Dr. {doctor.name} (so the list can be delivered).')
            appt_hour = now.hour
            appt_minute = now.minute
            appt = Appointment(
                doctor=doctor,
                patient=patient,
                patient_name=patient.full_name,
                patient_phone=patient.phone,
                reason='Email system test',
                day=tomorrow.day,
                month=tomorrow.month,
                year=tomorrow.year,
                hour=appt_hour,
                minute=appt_minute,
            )
            appt.save()
            self.stdout.write(f'Created test appointment #{appt.id} for tomorrow {tomorrow} {appt_hour:02d}:{appt_minute:02d}.')
        else:
            self.stdout.write(f'Test appointment #{appt.id} for tomorrow already exists.')

        # ---- 3. Run all three senders ----
        r1 = send_medication_reminders_for_current_time()
        r2 = send_appointment_reminders_due()
        r3 = send_doctor_patient_lists_due()
        return r1, r2, r3