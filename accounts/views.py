from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta
from .models import User, Doctor, Patient, Appointment, Medication, HealthReading, INSURANCE_CHOICES, PatientVisit, MedicalRecord, Prescription, PatientRecord
import logging
import json

logger = logging.getLogger(__name__)


def home(request):
    if request.user.is_authenticated:
        if request.user.role == 'patient':
            return redirect('patient_dashboard')
        elif request.user.role == 'doctor':
            return redirect('doctor_appointments')
        elif request.user.is_admin_user:
            return redirect('admin_panel')
        return redirect('patient_dashboard')
    doctors = Doctor.objects.all().order_by('medical_number')
    return render(request, 'landing.html', {'doctors': doctors})


@login_required
def patient_dashboard(request):
    logger.error("DASHBOARD DEBUG: user=%s, role=%s, is_authenticated=%s", request.user, getattr(request.user, 'role', 'NO ROLE'), request.user.is_authenticated)
    if request.user.role != 'patient':
        return redirect('home')

    try:
        patient = request.user.patient_profile
        logger.error("DASHBOARD DEBUG: patient found, first_name_encrypted=%s", patient.first_name_encrypted[:20] if patient.first_name_encrypted else 'EMPTY')
    except Exception as e:
        logger.error("PATIENT_DASH error for user %s: %s", request.user, e, exc_info=True)
        return redirect('google_complete_profile')

    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)
        weekday_map = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'}
        today_name = weekday_map[today.weekday()]

        meds_today = Medication.objects.filter(patient=patient, days_of_week__contains=today_name)
        reminders = []
        for med in meds_today:
            taken = (med.taken_days or '').split(',')
            if today_name not in taken:
                reminders.append({'type': 'medication', 'message': f"Time to take {med.name} ({med.dosage})", 'med': med})

        upcoming_appts = Appointment.objects.filter(
            patient=patient, is_cancelled=False,
            year=tomorrow.year, month=tomorrow.month, day=tomorrow.day,
        )
        for appt in upcoming_appts:
            reminders.append({'type': 'appointment', 'message': f"Appointment with Dr. {appt.doctor.name} tomorrow at {appt.hour:02d}:{appt.minute:02d}", 'appt': appt})
    except Exception as e:
        logger.error("REMINDERS error for user %s: %s", request.user, e, exc_info=True)
        reminders = []

    return render(request, 'patient_dashboard.html', {
        'reminders': reminders,
        'reminder_count': len(reminders),
        'reminders_json': json.dumps([{'type': r['type'], 'message': r['message']} for r in reminders]),
    })


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('home')
    if request.user.role == 'patient':
        return redirect('patient_dashboard')
    elif request.user.role == 'doctor':
        return redirect('doctor_appointments')
    elif request.user.is_admin_user:
        return redirect('admin_panel')
    return redirect('home')


def google_complete_profile(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.role != 'patient':
        return redirect('home')
    if hasattr(request.user, 'patient_profile'):
        return redirect('patient_dashboard')

    social = request.user.socialaccount_set.filter(provider='google').first()
    extra = social.extra_data if social else {}
    g_first = extra.get('given_name') or request.user.first_name or ''
    g_last = extra.get('family_name') or request.user.last_name or ''
    g_email = request.user.email or ''

    if request.method == 'POST':
        errors = []
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        age_raw = request.POST.get('age', '').strip()
        phone = request.POST.get('phone', '').strip()
        insurance = request.POST.getlist('insurance')

        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')
        try:
            age = int(age_raw)
            if age < 1 or age > 120:
                errors.append('Age must be between 1 and 120.')
        except ValueError:
            age = 0
            errors.append('Valid age is required.')
        import re as _re
        if not _re.fullmatch(r'09\d{9}', phone):
            errors.append('Phone must be 11 digits starting with 09.')
        else:
            for p in Patient.objects.exclude(user=request.user):
                try:
                    if p.phone == phone:
                        errors.append('This phone number is already registered.')
                        break
                except Exception:
                    continue

        if errors:
            return render(request, 'google_complete_profile.html', {
                'errors': errors,
                'insurance_choices': INSURANCE_CHOICES,
                'form_data': {
                    'first_name': first_name, 'last_name': last_name,
                    'age': age_raw, 'phone': phone, 'insurance': insurance,
                },
            })

        patient = Patient(user=request.user)
        patient.first_name = first_name
        patient.last_name = last_name
        patient.age = age
        patient.phone = phone
        patient.email = g_email
        patient.insurance = ','.join(insurance)
        patient.save()
        messages.success(request, 'Profile completed. Welcome!')
        return redirect('patient_dashboard')

    return render(request, 'google_complete_profile.html', {
        'insurance_choices': INSURANCE_CHOICES,
        'g_first': g_first,
        'g_last': g_last,
        'g_email': g_email,
    })


@login_required
def google_complete_doctor_profile(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.role != 'doctor':
        return redirect('home')
    if hasattr(request.user, 'doctor_profile'):
        return redirect('doctor_appointments')

    social = request.user.socialaccount_set.filter(provider='google').first()
    extra = social.extra_data if social else {}
    g_first = extra.get('given_name') or request.user.first_name or ''
    g_last = extra.get('family_name') or request.user.last_name or ''
    g_email = request.user.email or ''

    if request.method == 'POST':
        errors = []
        name = request.POST.get('name', '').strip()
        medical_number = request.POST.get('medical_number', '').strip()
        specialty = request.POST.get('specialty', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            errors.append('Doctor name is required.')
        if not medical_number or len(medical_number) != 4 or not medical_number.isdigit():
            errors.append('Medical number must be exactly 4 digits.')
        if Doctor.objects.filter(medical_number=medical_number).exists():
            errors.append('This medical number already exists.')
        if not specialty:
            errors.append('Specialty is required.')

        if errors:
            return render(request, 'google_complete_doctor_profile.html', {
                'errors': errors,
                'form_data': {
                    'name': name,
                    'medical_number': medical_number,
                    'specialty': specialty,
                    'description': description,
                },
                'g_first': g_first,
                'g_last': g_last,
                'g_email': g_email,
            })

        from accounts.models import Doctor
        from django.contrib.auth.hashers import make_password
        
        doctor = Doctor(user=request.user, medical_number=medical_number, specialty=specialty, description=description)
        doctor.name = name
        doctor.save()
        
        messages.success(request, 'Doctor profile completed. Welcome!')
        return redirect('doctor_appointments')

    return render(request, 'google_complete_doctor_profile.html', {
        'g_first': g_first,
        'g_last': g_last,
        'g_email': g_email,
    })


def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '').strip()

        if not identifier or not password:
            messages.error(request, 'Please fill in all fields.')
            return render(request, 'login.html')

        try:
            # Track what we tried for better error messages
            tried_admin = False
            tried_doctor = False
            tried_patient = False
            patient_found = False
            password_wrong = False

            # Try admin login first (username + password)
            user = authenticate(request, username=identifier, password=password)
            logger.error("LOGIN DEBUG: authenticate result=%s, is_admin=%s", user, user.is_admin_user if user else 'N/A')
            if user and user.is_admin_user:
                login(request, user)
                return redirect('admin_panel')
            tried_admin = True

            # Try doctor login (username or name, password = medical_number)
            try:
                doctor = Doctor.objects.get(user__username=identifier)
                logger.error("LOGIN DEBUG: found doctor by username: %s", doctor)
                tried_doctor = True
                if doctor.user.check_password(password):
                    login(request, doctor.user, backend='django.contrib.auth.backends.ModelBackend')
                    return redirect('doctor_appointments')
                else:
                    password_wrong = True
            except Doctor.DoesNotExist:
                pass

            try:
                doctors = Doctor.objects.select_related('user').all()
                matched_doctor = None
                for d in doctors:
                    if d.name.lower() == identifier.lower():
                        matched_doctor = d
                        break
                if matched_doctor:
                    logger.error("LOGIN DEBUG: found doctor by name: %s", matched_doctor)
                    tried_doctor = True
                    if matched_doctor.user.check_password(password):
                        login(request, matched_doctor.user, backend='django.contrib.auth.backends.ModelBackend')
                        return redirect('doctor_appointments')
                    else:
                        password_wrong = True
            except Doctor.DoesNotExist:
                pass

            # Try patient login (email/phone/username + password)
            matched_patient = None
            try:
                patients = Patient.objects.select_related('user').all()
                logger.error("LOGIN DEBUG: total patients=%d", patients.count())
                for p in patients:
                    try:
                        p_email = p.email
                        p_phone = p.phone
                        p_username = p.user.username
                        logger.error("LOGIN DEBUG: checking patient username=%s email_match=%s phone_match=%s", p_username, p_email == identifier, p_phone == identifier)
                        match = (p_email == identifier or p_phone == identifier or p_username == identifier)
                    except Exception as e:
                        logger.error("LOGIN DEBUG: decrypt error for patient: %s", e)
                        match = (p.user.username == identifier)
                    if match:
                        patient_found = True
                        pw_check = check_password(password, p.password_hash)
                        logger.error("LOGIN DEBUG: password check=%s for patient=%s", pw_check, p.user.username)
                        if pw_check:
                            matched_patient = p
                            break
                        else:
                            password_wrong = True
            except Exception as e:
                logger.error("LOGIN DEBUG: patient loop error: %s", e, exc_info=True)

            if matched_patient:
                logger.error("LOGIN DEBUG: logging in patient=%s", matched_patient.user.username)
                login(request, matched_patient.user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect('patient_dashboard')
            else:
                logger.error("LOGIN DEBUG: no matched patient for identifier=%s", identifier)
            tried_patient = True

            # Try admin with username (in case identifier is username)
            user = authenticate(request, username=identifier, password=password)
            if user and user.is_admin_user:
                login(request, user)
                return redirect('admin_panel')

            # More specific error messages
            if patient_found and password_wrong:
                messages.error(request, 'Wrong password for this account. Please try again.')
            elif tried_doctor and password_wrong:
                messages.error(request, 'Wrong medical number. Please check and try again.')
            elif tried_admin and not user:
                messages.error(request, 'No account found with that username/email/phone. Please check or register.')
            elif tried_patient and not patient_found:
                messages.error(request, 'No account found with that username, email, or phone. Please check or register.')
            else:
                messages.error(request, 'Invalid credentials. Please check your username/email/phone and password.')

            return render(request, 'login.html')

        except Exception as e:
            logger.error("Login view error for identifier '%s': %s", identifier, e, exc_info=True)
            messages.error(request, 'An error occurred. Please try again.')
            return render(request, 'login.html')

    return render(request, 'login.html')


def register_patient(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        age = request.POST.get('age', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        insurance_list = request.POST.getlist('insurance')
        insurance = ','.join(insurance_list)
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()

        errors = []

        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')
        if not age or not age.isdigit() or int(age) <= 0:
            errors.append('Valid age is required.')
        if not phone or len(phone) != 11 or not phone.startswith('09') or not phone.isdigit():
            errors.append('Phone must be 11 digits starting with 09.')
        # Accept Iranian local (09...) or worldwide E.164 (+countrycode...).
        if not phone:
            errors.append('Phone is required.')
        else:
            digits = ''.join(ch for ch in phone if ch.isdigit())
            if not digits.isdigit() or len(digits) < 10:
                errors.append('Phone must be a valid number (Iranian 09... or +countrycode...).')
            elif phone.startswith('+') and not phone.startswith('+98'):
                pass  # international number: fine
            elif not phone.startswith('09') or len(phone) != 11:
                if not phone.startswith('+'):
                    errors.append('Phone must be 11 digits starting with 09 (Iran) or start with + for international numbers.')
        if not email or '@' not in email:
            errors.append('Valid email is required.')
        if len(password1) < 8:
            errors.append('Password must be at least 8 characters long.')
        if password1.isalpha():
            errors.append('Password must contain at least one number.')
        if password1.isdigit():
            errors.append('Password must contain at least one letter.')
        if password1 != password2:
            errors.append('Passwords do not match.')
        if not insurance_list:
            errors.append('Please select at least one insurance provider.')

        if not errors:
            for p in Patient.objects.all():
                if p.phone == phone:
                    errors.append('This phone number is already registered.')
                    break
                if p.email == email:
                    errors.append('This email is already registered.')
                    break

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'register.html', {
                'insurance_choices': Patient.INSURANCE_CHOICES,
                'form_data': {'insurances': insurance_list, 'first_name': first_name, 'last_name': last_name, 'age': age, 'phone': phone, 'email': email},
            })

        base_username = first_name.lower().replace(' ', '')
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            password=password1,
            role='patient',
            email=email
        )

        patient = Patient(
            user=user,
            age=int(age),
            password_hash=make_password(password1),
            insurance=insurance
        )
        patient.first_name = first_name
        patient.last_name = last_name
        patient.phone = phone
        patient.email = email
        patient.save()

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'Registration successful! Your username is "{username}". Welcome!')
        return redirect('patient_dashboard')

    return render(request, 'register.html', {'insurance_choices': Patient.INSURANCE_CHOICES})


def logout_view(request):
    logout(request)
    return redirect('home')


# ==================== Patient Appointment Views ====================

@login_required
def patient_appointments(request):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        messages.error(request, 'Access denied.')
        return redirect('home')
    appointments = Appointment.objects.filter(patient=patient, is_cancelled=False).order_by('year', 'month', 'day', 'hour')
    cancelled = Appointment.objects.filter(patient=patient, is_cancelled=True).order_by('-year', '-month', '-day', '-hour')[:10]

    return render(request, 'appointments/patient_appointments.html', {
        'patient': patient,
        'appointments': appointments,
        'cancelled': cancelled,
    })


@login_required
def appointment_book(request):
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile

    patient_insurances = patient.get_insurance_list()

    specialty_filter = request.GET.get('specialty', '')
    insurance_filter = request.GET.get('insurance', '')

    doctors = list(Doctor.objects.all())

    if specialty_filter:
        doctors = [d for d in doctors if d.specialty.lower() == specialty_filter.lower()]

    if insurance_filter == 'my_insurance' and patient_insurances:
        doctors = [d for d in doctors if any(ins in d.get_accepted_insurance_list() for ins in patient_insurances)]
    elif insurance_filter and insurance_filter != 'my_insurance':
        doctors = [d for d in doctors if insurance_filter in d.get_accepted_insurance_list()]

    specialties = sorted(set(d.specialty for d in Doctor.objects.all()))

    selected_doctor = None
    booked_hours = []

    now = timezone.now()
    selected_day = None
    selected_month = now.month
    selected_year = now.year

    doctor_id = request.GET.get('doctor_id')
    day = request.GET.get('day')
    month = request.GET.get('month')
    year = request.GET.get('year')

    if month and year:
        selected_month = int(month)
        selected_year = int(year)

    if selected_month < 1:
        selected_month = 12
        selected_year -= 1
    elif selected_month > 12:
        selected_month = 1
        selected_year += 1

    if day:
        selected_day = int(day)

    if doctor_id:
        selected_doctor = get_object_or_404(Doctor, id=doctor_id)

        if selected_day is not None:
            booked_appointments = Appointment.objects.filter(
                doctor=selected_doctor,
                day=selected_day,
                month=selected_month,
                year=selected_year,
                is_cancelled=False
            )
            booked_hours = [a.hour for a in booked_appointments]

    import calendar as cal
    cal_obj = cal.Calendar(firstweekday=5)
    month_days = cal_obj.monthdayscalendar(selected_year, selected_month)
    month_name = cal.month_name[selected_month]

    if selected_month == 12:
        next_month, next_year = 1, selected_year + 1
    else:
        next_month, next_year = selected_month + 1, selected_year

    if selected_month == 1:
        prev_month, prev_year = 12, selected_year - 1
    else:
        prev_month, prev_year = selected_month - 1, selected_year

    calendar_weekdays = []
    for week in month_days:
        for d in week:
            if d == 0:
                continue
            try:
                dt = date(selected_year, selected_month, d)
                is_weekday = dt.weekday() not in (5, 6)
                is_past = dt < now.date()
                calendar_weekdays.append({
                    'day': d,
                    'weekday': dt.weekday(),
                    'name': cal.day_abbr[dt.weekday()],
                    'is_weekday': is_weekday,
                    'is_past': is_past,
                    'is_today': dt == now.date(),
                    'is_selected': selected_day == d,
                })
            except ValueError:
                pass

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        day = int(request.POST.get('day'))
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
        hour = int(request.POST.get('hour'))
        reason = request.POST.get('reason', '').strip()

        doctor = get_object_or_404(Doctor, id=doctor_id)

        from datetime import date as dt_date
        try:
            check_date = dt_date(year, month, day)
            if check_date.weekday() in (5, 6):
                messages.error(request, 'Cannot book appointments on Saturday or Sunday.')
                return redirect(f"{request.path}?doctor_id={doctor_id}")
        except ValueError:
            pass

        if hour < 8 or hour > 17:
            messages.error(request, 'Please select a time between 8 AM and 6 PM.')
        elif Appointment.objects.filter(
            doctor=doctor,
            day=day,
            month=month,
            year=year,
            hour=hour,
            is_cancelled=False
        ).exists():
            messages.error(request, 'The selected time is already booked.')
        else:
            appointment = Appointment(
                doctor=doctor,
                patient=patient,
                patient_name=patient.full_name,
                patient_phone=patient.phone,
                reason=reason,
                day=day,
                month=month,
                year=year,
                hour=hour,
            )
            appointment.save()
            messages.success(request, 'Appointment booked successfully!')
            return redirect('patient_appointments')

    return render(request, 'appointments/book_appointment.html', {
        'patient': patient,
        'doctors': doctors,
        'selected_doctor': selected_doctor,
        'booked_hours': booked_hours,
        'selected_day': selected_day,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'month_name': month_name,
        'month_days': month_days,
        'calendar_weekdays': calendar_weekdays,
        'hours': range(8, 18),
        'insurance_choices': INSURANCE_CHOICES,
        'insurance_filter': insurance_filter,
        'patient_insurance': patient.insurance,
        'patient_insurances': patient_insurances,
        'specialties': specialties,
        'specialty_filter': specialty_filter,
    })


@login_required
def appointment_cancel(request, appointment_id):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)
    appointment.is_cancelled = True
    appointment.save()
    messages.success(request, 'Appointment cancelled successfully.')
    return redirect('patient_appointments')


@login_required
def appointment_delete(request, appointment_id):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=patient)
    appointment.delete()
    messages.success(request, 'Appointment deleted permanently.')
    return redirect('patient_appointments')


# ==================== Doctor Appointment Views ====================

from datetime import date as dt_date

@login_required
def doctor_appointments(request):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    doctor = request.user.doctor_profile
    appointments = Appointment.objects.filter(doctor=doctor, is_cancelled=False).select_related('visit').order_by('year', 'month', 'day', 'hour')

    grouped = {}
    day_names = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}
    for appt in appointments:
        try:
            d = dt_date(appt.year, appt.month, appt.day)
            key = d.isoformat()
        except ValueError:
            key = f"{appt.year}-{appt.month:02d}-{appt.day:02d}"
            d = None

        if key not in grouped:
            if d:
                grouped[key] = {
                    'date': d,
                    'day_name': day_names.get(d.weekday(), ''),
                    'display': d.strftime('%b %d, %Y'),
                    'appointments': [],
                }
            else:
                grouped[key] = {
                    'date': None,
                    'day_name': '',
                    'display': f"{appt.year}/{appt.month}/{appt.day}",
                    'appointments': [],
                }

        try:
            patient = appt.patient
            insurance = patient.get_insurance_display_name()
        except Exception:
            insurance = 'Unknown'

        try:
            is_completed = bool(appt.visit.is_completed)
        except Exception:
            is_completed = False

        grouped[key]['appointments'].append({
            'id': appt.id,
            'patient_name': appt.patient_name,
            'patient_phone': appt.patient_phone,
            'time': f"{appt.hour:02d}:{appt.minute:02d}",
            'reason': appt.reason,
            'insurance': insurance,
            'is_completed': is_completed,
        })

    try:
        import zoneinfo
        tehran = zoneinfo.ZoneInfo('Asia/Tehran')
        today = timezone.now().astimezone(tehran).date()
    except Exception:
        today = dt_date.today()
    valid_dates = [g['date'] for g in grouped.values() if g['date']]
    default_key = today.isoformat() if today in valid_dates else None

    for key, g in grouped.items():
        g['is_past'] = bool(g['date'] and g['date'] < today)
        g['is_today'] = bool(g['date'] and g['date'] == today)
        g['done_count'] = sum(1 for a in g['appointments'] if a['is_completed'])
        g['appointments'].sort(key=lambda a: a['time'], reverse=True)
        g['is_open'] = (key == default_key)

    sorted_days = sorted(grouped.values(), key=lambda x: x['date'] if x['date'] else dt_date.max, reverse=True)

    return render(request, 'appointments/doctor_appointments.html', {
        'doctor': doctor,
        'appointments': appointments,
        'grouped_days': sorted_days,
        'total_count': appointments.count(),
    })


# ==================== Admin Views ====================

@login_required
def admin_panel(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied. Admins only.')
        return redirect('home')

    doctors = Doctor.objects.all()
    appointments = Appointment.objects.filter(is_cancelled=False).order_by('year', 'month', 'day', 'hour')
    regular_users = User.objects.filter(is_admin_user=False)
    admin_users = User.objects.filter(is_admin_user=True).exclude(username='sam')

    return render(request, 'admin/dashboard.html', {
        'doctors': doctors,
        'appointments': appointments,
        'regular_users': regular_users,
        'admin_users': admin_users,
    })


@login_required
def admin_add_doctor(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied. Admins only.')
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        medical_number = request.POST.get('medical_number', '').strip()

        errors = []
        if not name:
            errors.append('Doctor name is required.')
        if not medical_number or len(medical_number) != 4 or not medical_number.isdigit():
            errors.append('Medical number must be exactly 4 digits.')
        if Doctor.objects.filter(medical_number=medical_number).exists():
            errors.append('This medical number already exists.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            base_username = name.lower().replace(' ', '')
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Generate unique medical_id
            medical_id = medical_number
            counter = 1
            while Doctor.objects.filter(medical_id=medical_id).exists():
                medical_id = f"{medical_number}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                password=medical_number,
                role='doctor'
            )
            doctor = Doctor(user=user, medical_number=medical_number, medical_id=medical_id)
            doctor.name = name
            doctor.save()
            messages.success(request, f'Dr. {name} added! Username: {username}')
            return redirect('admin_panel')

    return render(request, 'admin/add_doctor.html')


@login_required
def admin_promote_user(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied. Admins only.')
        return redirect('home')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')

        try:
            user = User.objects.get(id=user_id, is_admin_user=False)
            user.is_admin_user = True
            user.role = 'admin'
            user.save()
            messages.success(request, f'{user.username} has been promoted to admin!')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')

        return redirect('admin_panel')

    regular_users = User.objects.filter(is_admin_user=False)
    return render(request, 'admin/promote_user.html', {'regular_users': regular_users})


@login_required
def admin_demote_user(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied. Admins only.')
        return redirect('home')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')

        try:
            user = User.objects.get(id=user_id, is_admin_user=True)
            if user.username == 'sam':
                messages.error(request, 'Cannot remove the main admin.')
            else:
                user.is_admin_user = False
                user.role = 'patient'
                user.save()
                messages.success(request, f'{user.username} has been removed from admin.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')

        return redirect('admin_panel')

    return redirect('admin_panel')


@login_required
def admin_remove_user(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied. Admins only.')
        return redirect('home')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')

        try:
            user = User.objects.get(id=user_id, is_admin_user=False)
            if user.username == 'sam':
                messages.error(request, 'Cannot remove the main admin.')
            else:
                username = user.username
                user.delete()
                messages.success(request, f'User "{username}" removed from the site.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')

        return redirect('admin_panel')

    return redirect('admin_panel')


# ==================== Medication Views ====================

@login_required
def medication_list(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile
    medications = Medication.objects.filter(patient=patient).order_by('time')

    return render(request, 'medications/medication_list.html', {
        'patient': patient,
        'medications': medications,
        'days': Medication.DAYS_OF_WEEK,
    })


@login_required
def medication_add(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        dosage = request.POST.get('dosage', '').strip()
        times_per_day = int(request.POST.get('times_per_day', 1))
        days_list = request.POST.getlist('days_of_week')
        days_str = ','.join(days_list)

        errors = []
        if not name:
            errors.append('Medication name is required.')
        if not dosage:
            errors.append('Dosage is required.')
        if not days_list:
            errors.append('Please select at least one day.')

        times_list = []
        for i in range(1, times_per_day + 1):
            t = request.POST.get(f'time_{i}', '').strip()
            if not t:
                errors.append(f'Time {i} is required.')
            else:
                times_list.append(t)

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            try:
                from datetime import time as dt_time
                from django.utils import timezone
                now = timezone.now()
                first_hour, first_minute = map(int, times_list[0].split(':'))
                times_str = ','.join(times_list)
                med = Medication(
                    patient=patient,
                    time=dt_time(first_hour, first_minute),
                    times_of_day=times_str,
                    times_per_day=times_per_day,
                    days_of_week=days_str,
                    hour=first_hour,
                    day=now.day,
                    month=now.month,
                    year=now.year,
                )
                med.name = name
                med.dosage = dosage
                med.save()
                messages.success(request, 'Medication added successfully!')
                return redirect('medication_list')
            except ValueError:
                messages.error(request, 'Invalid time format. Use HH:MM.')

    return render(request, 'medications/medication_add.html', {
        'patient': patient,
        'days': Medication.DAYS_OF_WEEK,
    })


@login_required
def medication_delete(request, med_id):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile
    med = get_object_or_404(Medication, id=med_id, patient=patient)
    med.delete()
    messages.success(request, 'Medication deleted.')
    return redirect('medication_list')


@login_required
def medication_toggle_taken(request, med_id):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile
    med = get_object_or_404(Medication, id=med_id, patient=patient)
    day = request.GET.get('day') or request.POST.get('day', '')
    taken_days = (med.taken_days or '').split(',')
    if day in taken_days:
        taken_days.remove(day)
    elif day:
        taken_days.append(day)
    med.taken_days = ','.join(d for d in taken_days if d)
    med.save()
    url = reverse('medication_by_day')
    if day:
        url += f'?day={day}'
    return redirect(url)


@login_required
def medication_by_day(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile
    selected_day = request.GET.get('day', '')
    medications = []

    if selected_day:
        all_meds = Medication.objects.filter(patient=patient).order_by('time')
        medications = [m for m in all_meds if selected_day in m.days_of_week.split(',')]
        for m in medications:
            m.is_taken = selected_day in (m.taken_days.split(',') if m.taken_days else [])
            m.toggle_url = f"{reverse('medication_toggle_taken', args=[m.id])}?day={selected_day}"

    return render(request, 'medications/medication_by_day.html', {
        'patient': patient,
        'medications': medications,
        'selected_day': selected_day,
        'days': Medication.DAYS_OF_WEEK,
    })


# ==================== Health Views ====================

@login_required
def health_dashboard(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile
    readings = HealthReading.objects.filter(patient=patient).order_by('-year', '-month', '-day', '-hour')

    return render(request, 'health/dashboard.html', {
        'patient': patient,
        'readings': readings,
    })


@login_required
def health_add(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile

    if request.method == 'POST':
        reading_type = request.POST.get('reading_type', '').strip()
        systolic = request.POST.get('systolic', '0').strip()
        diastolic = request.POST.get('diastolic', '0').strip()
        value = request.POST.get('value', '0').strip()

        from django.utils import timezone
        now = timezone.now()

        errors = []
        if not reading_type:
            errors.append('Reading type is required.')

        if reading_type == 'blood_pressure':
            if not systolic or not diastolic:
                errors.append('Both systolic and diastolic values are required.')
            else:
                try:
                    systolic = int(systolic)
                    diastolic = int(diastolic)
                except ValueError:
                    errors.append('Invalid blood pressure values.')
        else:
            if not value:
                errors.append('Value is required.')
            else:
                try:
                    value = int(value)
                except ValueError:
                    errors.append('Invalid value.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            reading = HealthReading(
                patient=patient,
                reading_type=reading_type,
                systolic=int(systolic) if systolic else 0,
                diastolic=int(diastolic) if diastolic else 0,
                value=int(value) if value else 0,
                hour=now.hour,
                day=now.day,
                month=now.month,
                year=now.year,
            )
            reading.save()
            messages.success(request, 'Health reading added successfully!')
            return redirect('health_dashboard')

    return render(request, 'health/add_reading.html', {
        'patient': patient,
        'types': HealthReading.READING_TYPES,
    })


@login_required
def health_delete(request, reading_id):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile
    reading = get_object_or_404(HealthReading, id=reading_id, patient=patient)
    reading.delete()
    messages.success(request, 'Health reading deleted.')
    return redirect('health_dashboard')


@login_required
def health_chart(request):
    if not hasattr(request.user, 'patient_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    patient = request.user.patient_profile
    readings = HealthReading.objects.filter(patient=patient).order_by('year', 'month', 'day', 'hour')

    return render(request, 'health/chart.html', {
        'patient': patient,
        'readings': readings,
    })


@login_required
def doctor_insurance_settings(request):
    try:
        doctor = request.user.doctor_profile
    except Exception:
        messages.error(request, 'Access denied.')
        return redirect('home')

    if request.method == 'POST':
        selected = request.POST.getlist('accepted_insurance')
        doctor.accepted_insurance = ','.join(selected)
        doctor.save()
        messages.success(request, 'Insurance settings saved.')
        return redirect('doctor_appointments')

    return render(request, 'appointments/doctor_insurance_settings.html', {
        'doctor': doctor,
        'insurance_choices': INSURANCE_CHOICES,
    })


@login_required
def doctor_patient_visit(request, appointment_id):
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Access denied.')
        return redirect('home')

    doctor = request.user.doctor_profile
    try:
        appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('doctor_appointments')

    patient = appointment.patient

    visit, created = PatientVisit.objects.get_or_create(
        appointment=appointment,
        doctor=doctor,
        patient=patient,
        defaults={
            'blood_type': patient.blood_type,
            'allergies': patient.allergies,
            'disease_history': patient.disease_history,
        },
    )

    past_visits = PatientVisit.objects.filter(
        doctor=doctor, patient=patient, is_completed=True
    ).order_by('-visited_at')[:10]

    medications = Medication.objects.filter(patient=patient)
    health_readings = HealthReading.objects.filter(patient=patient).order_by('-created_at')[:20]

    readings_chart = []
    for r in HealthReading.objects.filter(patient=patient).order_by('year', 'month', 'day', 'hour')[:40]:
        entry = {'t': r.reading_type, 'l': f"{r.year}/{r.month}/{r.day}"}
        if r.reading_type == 'blood_pressure':
            entry['a'] = r.systolic
            entry['b'] = r.diastolic
        else:
            entry['v'] = r.value
        readings_chart.append(entry)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'save_info':
            blood = request.POST.get('blood_type', '').strip()
            allerg = request.POST.get('allergies', '').strip()
            disease = request.POST.get('disease_history', '').strip()
            notes = request.POST.get('notes', '').strip()
            visit.blood_type = blood
            visit.allergies = allerg
            visit.disease_history = disease
            visit.notes = notes
            visit.save()
            patient.blood_type = blood
            patient.allergies = allerg
            patient.disease_history = disease
            patient.save()
            messages.success(request, 'Patient info saved.')

        elif action == 'upload_record':
            title = request.POST.get('record_title', '').strip()
            file = request.FILES.get('record_file')
            if title and file:
                MedicalRecord.objects.create(visit=visit, title=title, file=file)
                messages.success(request, f'Record "{title}" uploaded.')
            else:
                messages.error(request, 'Title and file are required.')

        elif action == 'add_prescription':
            text = request.POST.get('prescription_text', '').strip()
            file = request.FILES.get('prescription_file')
            if text or file:
                Prescription.objects.create(visit=visit, text=text, file=file)
                messages.success(request, 'Prescription added.')
            else:
                messages.error(request, 'Enter prescription text or upload a file.')

        elif action == 'mark_visited':
            blood = request.POST.get('blood_type', visit.blood_type).strip()
            allerg = request.POST.get('allergies', visit.allergies).strip()
            disease = request.POST.get('disease_history', visit.disease_history).strip()
            notes = request.POST.get('notes', visit.notes).strip()
            visit.blood_type = blood
            visit.allergies = allerg
            visit.disease_history = disease
            visit.notes = notes
            visit.is_completed = True
            from django.utils import timezone as tz
            visit.visited_at = tz.now()
            visit.save()
            patient.blood_type = blood
            patient.allergies = allerg
            patient.disease_history = disease
            patient.save()
            messages.success(request, f'Visit with {patient.full_name} marked as completed.')
            return redirect('doctor_appointments')

        elif action == 'undo_visit':
            visit.is_completed = False
            visit.visited_at = None
            visit.save()
            messages.success(request, 'Visit uncompleted. You can continue editing.')

        return redirect('doctor_patient_visit', appointment_id=appointment_id)

    records = visit.medical_records.all()
    prescriptions = visit.prescriptions.all()

    return render(request, 'appointments/doctor_patient_visit.html', {
        'doctor': doctor,
        'appointment': appointment,
        'patient': patient,
        'visit': visit,
        'past_visits': past_visits,
        'medications': medications,
        'health_readings': health_readings,
        'readings_chart': readings_chart,
        'records': records,
        'prescriptions': prescriptions,
        'patient_records': PatientRecord.objects.filter(patient=patient).order_by('-created_at'),
    })


@login_required
def patient_records(request):
    if request.user.role != 'patient':
        return redirect('home')
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('home')
    records = PatientRecord.objects.filter(patient=patient).order_by('-created_at')
    return render(request, 'patient_records.html', {'patient': patient, 'records': records})


@login_required
def patient_record_add(request):
    if request.user.role != 'patient':
        return redirect('home')
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return redirect('home')

    appointments = Appointment.objects.filter(patient=patient, is_cancelled=False).order_by('-year', '-month', '-day')

    if request.method == 'POST':
        symptoms = request.POST.get('symptoms', '').strip()
        notes = request.POST.get('notes', '').strip()
        appointment_id = request.POST.get('appointment_id', '')
        uploaded_file = request.FILES.get('file', None)

        if not symptoms:
            messages.error(request, 'Please describe your symptoms.')
            return render(request, 'patient_record_add.html', {'patient': patient, 'appointments': appointments})

        appointment = None
        if appointment_id:
            try:
                appointment = Appointment.objects.get(id=appointment_id, patient=patient)
            except Appointment.DoesNotExist:
                pass

        PatientRecord.objects.create(
            patient=patient,
            appointment=appointment,
            symptoms=symptoms,
            notes=notes,
            file=uploaded_file,
        )
        messages.success(request, 'Medical record added successfully.')
        return redirect('patient_records')

    return render(request, 'patient_record_add.html', {'patient': patient, 'appointments': appointments})


@csrf_exempt
def email_diagnostics(request):
    """Read-only email config status (no secrets). Useful for debugging deploys."""
    from django.conf import settings
    from accounts.models import EmailLog

    log_keys = list(EmailLog.objects.order_by('created_at').values_list('key', flat=True))
    config = {
        'backend': settings.EMAIL_BACKEND,
        'host': settings.EMAIL_HOST,
        'port': settings.EMAIL_PORT,
        'use_tls': settings.EMAIL_USE_TLS,
        'use_ssl': settings.EMAIL_USE_SSL,
        'host_user_set': bool(settings.EMAIL_HOST_USER),
        'host_password_set': bool(settings.EMAIL_HOST_PASSWORD),
        'default_from': settings.DEFAULT_FROM_EMAIL,
        'clinic_tz': settings.CLINIC_TIME_ZONE,
        'maileroo_key_set': bool(settings.MAILEROO_API_KEY),
        'delivery': 'MAILEROO_HTTPS_API' if settings.MAILEROO_API_KEY else 'DJANGO_BACKEND(via SMTP/console)',
        'sms': None,
        'telegram': None,
    }
    from accounts.sms import sms_provider_status
    config['sms'] = sms_provider_status()
    from accounts.telegram import bot_status
    config['telegram'] = bot_status()

    import json
    from django.http import JsonResponse

    if request.method == 'POST' and request.POST.get('probe') == '1':
        import socket
        test_hosts = [
            ('smtp.gmail.com', 465, 'SMTP_SSL'),
            ('smtp.gmail.com', 587, 'SMTP_TLS'),
            ('google.com', 443, 'HTTPS'),
            ('api.telegram.org', 443, 'TELEGRAM_API'),
        ]
        results = []
        for host, port, label in test_hosts:
            for family_name, family in [('IPv4', socket.AF_INET), ('IPv6', socket.AF_INET6)]:
                sock = None
                try:
                    sock = socket.socket(family, socket.SOCK_STREAM)
                    sock.settimeout(8)
                    sock.connect((host, port))
                    results.append(f'{label}/{host}:{port} {family_name}=OK')
                except Exception as e:
                    results.append(f'{label}/{host}:{port} {family_name}=FAIL({e})')
                finally:
                    if sock:
                        try:
                            sock.close()
                        except Exception:
                            pass
        return JsonResponse({'config': config, 'email_log': log_keys, 'tcp_probe': results})

    return JsonResponse({'config': config, 'email_log': log_keys})


@csrf_exempt
def telegram_webhook(request, secret=None):
    """Telegram pushes updates here. Sends them to accounts/telegram.handle_update()."""
    from django.conf import settings
    from django.http import JsonResponse
    from accounts.telegram import bot_enabled, handle_update
    try:
        from django.utils.encoding import force_str
    except ImportError:
        force_str = str

    if not bot_enabled():
        return JsonResponse({'ok': False, 'error': 'bot not configured'}, status=503)
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        return JsonResponse({'ok': False, 'error': 'bad secret'}, status=403)

    try:
        raw = request.body
        update = json.loads(raw.decode('utf-8'))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid json'}, status=400)

    result = handle_update(update)
    return JsonResponse({'ok': True, 'result': result})


@login_required
def telegram_connect(request):
    """Generate a fresh deep link so the logged-in user can connect their Telegram."""
    from django.conf import settings
    from accounts.telegram import generate_link_token, bot_link, bot_enabled, webhook_url

    if not bot_enabled():
        messages.error(request, 'The ClinicOS Telegram bot is not configured yet.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    token = generate_link_token(request.user)
    link = bot_link(token)
    if not link:
        messages.error(request, 'Telegram bot username is not configured on the server.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # Refresh webhook so Telegram always points at this deploy's URL.
    from accounts.telegram import set_webhook
    try:
        set_webhook(webhook_url(request))
    except Exception as e:
        logger.warning('telegram_connect set_webhook failed: %s', e)

    # Take the user straight to Telegram so the /start <token> lands on the bot.
    return redirect(link)


@login_required
def telegram_disconnect(request):
    """Remove the Telegram chat binding for the current user."""
    request.user.telegram_chat_id = ''
    request.user.save(update_fields=['telegram_chat_id'])
    messages.info(request, 'Your Telegram was disconnected.')
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def test_doctor_list_now(request):
    """Trigger the doctor patient list for TODAY right now (admin only)."""
    if not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Admin only')
    from accounts.email_utils import send_doctor_patient_lists_for_day, _clinic_today
    today = _clinic_today()
    result = send_doctor_patient_lists_for_day(today, force=True)
    from django.http import JsonResponse
    return JsonResponse({'date': str(today), 'result': result})
