from datetime import datetime as dt, timedelta, time as dtime

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.encryption import encrypt_data
from accounts.models import (
    Appointment,
    Doctor,
    HealthReading,
    Medication,
    Patient,
    PatientRecord,
    PatientSchedule,
    PatientVisit,
    Prescription,
)
from accounts.email_utils import _clinic_today

User = get_user_model()

DEMO_USERS = ['demopatient', 'demoleila', 'demohassan']


class Command(BaseCommand):
    help = ('Seed a rich, presentation-ready demo dataset: 3 patients, '
            'medications, health readings, schedule items, appointments for '
            'today/tomorrow, and one completed visit with prescription.')

    def handle(self, *args, **options):
        # Base data must exist first (admin + doctors).
        call_command('seed_admin')
        call_command('seed_doctors')

        today = _clinic_today()

        # --- Clean previous demo data (keep other accounts) ---
        for model in (PatientVisit, PatientRecord, HealthReading):
            model.objects.filter(patient__user__username__in=DEMO_USERS).delete()
        Prescription.objects.filter(visit__patient__user__username__in=DEMO_USERS).delete()
        Medication.objects.filter(patient__user__username__in=DEMO_USERS).delete()
        PatientSchedule.objects.filter(patient__user__username__in=DEMO_USERS).delete()
        Appointment.objects.filter(patient__user__username__in=DEMO_USERS).delete()
        Patient.objects.filter(user__username__in=DEMO_USERS).delete()
        User.objects.filter(username__in=DEMO_USERS).delete()

        doctors = {d.user.username: d for d in Doctor.objects.all()}
        if not doctors:
            self.stderr.write('No doctors found; seed_doctors failed.')
            return
        dr = list(doctors.values())

        # --- Patient 1: main demo patient with full profile ---
        p1 = self._make_patient(
            username='demopatient', first='Samin', last='Mousapour', age=34,
            phone='+989121000001', email='demopatient@test.com',
            insurance='bimeh_salamat', blood_type='A+',
            allergies='Penicillin', disease_history='Mild hypertension',
        )

        # Medications: full day visibility
        meds_meta = [
            ('Aspirin', '100mg', '08:00'),
            ('Metformin', '500mg', '08:00,20:00'),
            ('Atorvastatin', '20mg', '21:00'),
        ]
        for name, dosage, times in meds_meta:
            self._make_medication(p1, name, dosage, times)

        # Health readings: ~14 days so the chart shows lines
        self._seed_readings(p1)

        # Weekly schedule items
        schedule_meta = [
            ('English class', 'class', 'tuesday', '18:00', '19:30', 'Milad Language Institute', '#8b5cf6'),
            ('Gym', 'exercise', 'monday', '07:00', '08:00', 'FitLife Gym', '#06b6d4'),
            ('Gym', 'exercise', 'wednesday', '07:00', '08:00', 'FitLife Gym', '#06b6d4'),
            ('Gym', 'exercise', 'friday', '07:00', '08:00', 'FitLife Gym', '#06b6d4'),
            ('Dentist appointment', 'appointment', 'saturday', '10:30', '11:30', 'Dr. Ahmadi Dental Clinic', '#ef4444'),
            ('Family dinner', 'personal', 'friday', '20:00', '22:00', 'Parents home', '#f59e0b'),
            ('Work', 'work', 'sunday', '09:00', '17:00', 'Tech Co. Office', '#10b981'),
        ]
        for title, cat, dow, start, end, loc, color in schedule_meta:
            self._make_schedule_item(p1, title, cat, dow, start, end, loc, color)

        # Appointments: one today, one tomorrow, plus a past completed one
        doc1 = dr[0]
        doc2 = next((d for d in dr if d.id != doc1.id), dr[-1])
        doc3 = next((d for d in dr if d.id not in (doc1.id, doc2.id)), doc1)
        self._make_appointment(p1, doc1, today, 10, 0, 'Routine check-up')
        self._make_appointment(p1, doc2, today + timedelta(days=1), 14, 30, 'Follow-up visit')
        past = today - timedelta(days=7)
        past_appt = self._make_appointment(p1, doc3, past, 9, 0, 'Annual physical')

        # Completed visit + prescription + note record for the doctor flow
        visit = PatientVisit.objects.create(
            appointment=past_appt, doctor=doc3, patient=p1,
            blood_type=p1.blood_type,
            allergies=p1.allergies,
            disease_history=p1.disease_history,
            notes='Patient reported occasional dizziness. BP stable. Advised hydration and sodium reduction.',
            is_completed=True,
        )
        try:
            visit.visited_at = past_appt.created_at
            visit.save()
        except Exception:
            pass
        Prescription.objects.create(
            visit=visit,
            text='Aspirin 100mg daily after breakfast. Atorvastatin 20mg at night. Review in 6 weeks.',
        )
        PatientRecord.objects.create(
            patient=p1, appointment=past_appt,
            symptoms='Occasional mild headaches and dizziness for ~2 weeks',
            notes='Worse in the evening, better after breakfast.',
        )

        # --- Patient 2: lighter profile ---
        p2 = self._make_patient(
            username='demoleila', first='Leila', last='Karimi', age=41,
            phone='+989121000002', email='demoleila@test.com',
            insurance='bimeh_tamin_ejtemaei', blood_type='B+',
            allergies='', disease_history='Type 2 diabetes',
        )
        self._make_medication(p2, 'Insulin Glargine', '10 units', '21:00')
        self._seed_readings(p2, days=7)
        self._make_schedule_item(p2, 'Physiotherapy', 'exercise', 'thursday', '16:00', '17:00', 'Rehab Center', '#06b6d4')
        self._make_appointment(p2, doc1, today, 11, 0, 'Diabetes follow-up')
        self._make_appointment(p2, doc2, today + timedelta(days=1), 9, 0, 'Lab results review')

        # --- Patient 3: lightest, for the Users table ---
        p3 = self._make_patient(
            username='demohassan', first='Hassan', last='Rezaei', age=58,
            phone='+989121000003', email='demohassan@test.com',
            insurance='bimeh_iran', blood_type='O-',
            allergies='Sulfa drugs', disease_history='Hypertension',
        )
        self._make_medication(p3, 'Losartan', '50mg', '08:00')
        self._make_appointment(p3, doc3, today, 16, 0, 'Blood pressure check')

        self.stdout.write(self.style.SUCCESS('''
Demo data ready:
  Patient (main):  demopatient / DemoPass123
  Patient:         demoleila   / DemoPass123
  Patient:         demohassan  / DemoPass123
  Doctor:          e.g. davidmaxwell / 1001   (login by username or name)
  Admin:           sam          (use the real admin password)

Checklist:
  - Patient dashboard, schedule board, meds, health chart, appointments
  - Doctor panel: davidmaxwell has appointments today + tomorrow
  - Admin panel: 3 demo patients, 10 doctors, appointments list
'''))

    # --- helpers ---

    def _make_patient(self, username, first, last, age, phone, email,
                      insurance, blood_type, allergies, disease_history):
        user = User.objects.create_user(
            username=username, password='DemoPass123', role='patient', email=email,
        )
        return Patient.objects.create(
            user=user,
            first_name_encrypted=encrypt_data(first),
            last_name_encrypted=encrypt_data(last),
            age=age,
            phone_encrypted=encrypt_data(phone),
            email_encrypted=encrypt_data(email),
            insurance=insurance,
            blood_type=blood_type,
            allergies=allergies,
            disease_history=disease_history,
            password_hash=user.password,
        )

    def _make_medication(self, patient, name, dosage, times):
        from datetime import datetime as dt
        all_days = 'monday,tuesday,wednesday,thursday,friday,saturday,sunday'
        first_time = times.split(',')[0]
        parsed = dt.strptime(first_time, '%H:%M').time()
        today = _clinic_today()
        return Medication.objects.create(
            patient=patient,
            name_encrypted=encrypt_data(name),
            dosage_encrypted=encrypt_data(dosage),
            time=parsed,
            times_of_day=times,
            times_per_day=len(times.split(',')),
            days_of_week=all_days,
            hour=parsed.hour,
            day=today.day,
            month=today.month,
            year=today.year,
        )

    def _make_schedule_item(self, patient, title, category, dow, start, end, loc, color):
        from datetime import time as dtime
        sh, sm = map(int, start.split(':'))
        eh, em = map(int, end.split(':'))
        return PatientSchedule.objects.create(
            patient=patient, title=title, category=category,
            day_of_week=dow, start_time=dtime(sh, sm), end_time=dtime(eh, em),
            location=loc, color=color, is_active=True,
        )

    def _make_appointment(self, patient, doctor, d, hour, minute, reason):
        return Appointment.objects.create(
            doctor=doctor, patient=patient,
            patient_name=patient.full_name, patient_phone=patient.phone,
            reason=reason, day=d.day, month=d.month, year=d.year,
            hour=hour, minute=minute,
        )

    def _seed_readings(self, patient, days=14):
        import random
        rng = random.Random(f'clinic-demo-{patient.user.username}')
        from datetime import timedelta
        today = _clinic_today()
        for i in range(days):
            d = today - timedelta(days=days - 1 - i)
            # Blood pressure: 2 samples/day
            bp_systolic = 118 + rng.randint(0, 12)
            bp_diastolic = 76 + rng.randint(0, 8)
            HealthReading.objects.create(
                patient=patient, reading_type='blood_pressure',
                systolic=bp_systolic, diastolic=bp_diastolic,
                hour=9, day=d.day, month=d.month, year=d.year,
            )
            HealthReading.objects.create(
                patient=patient, reading_type='blood_pressure',
                systolic=bp_systolic + rng.randint(-3, 3),
                diastolic=bp_diastolic + rng.randint(-2, 2),
                hour=19, day=d.day, month=d.month, year=d.year,
            )
            # Blood sugar: 1 sample/day
            HealthReading.objects.create(
                patient=patient, reading_type='blood_sugar',
                value=92 + rng.randint(-8, 14),
                day=d.day, month=d.month, year=d.year, hour=8,
            )
            # Heart rate: 1 sample/day
            HealthReading.objects.create(
                patient=patient, reading_type='heart_rate',
                value=66 + rng.randint(-4, 8),
                day=d.day, month=d.month, year=d.year, hour=12,
            )