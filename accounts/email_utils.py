from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import date, timedelta, datetime, time
from accounts.models import Appointment, Medication


def send_appointment_reminder_email(appointment):
    """
    Send appointment reminder email to patient one day before appointment.
    """
    patient = appointment.patient
    patient_email = patient.email
    patient_name = patient.full_name
    doctor_name = appointment.doctor.name
    doctor_specialty = appointment.doctor.specialty
    
    # Format appointment date and time
    appointment_date = date(appointment.year, appointment.month, appointment.day)
    appointment_time = f"{appointment.hour:02d}:{appointment.minute:02d}"
    
    # Prepare context for email template
    context = {
        'patient_name': patient_name,
        'doctor_name': doctor_name,
        'doctor_specialty': doctor_specialty,
        'appointment_date': appointment_date.strftime('%B %d, %Y'),
        'appointment_time': appointment_time,
        'appointment_day': appointment_date.strftime('%A'),
        'reason': appointment.reason,
        'clinic_name': 'ClinicOS',
    }
    
    # Render email content
    subject = f'Appointment Reminder: {doctor_name} tomorrow at {appointment_time}'
    
    # Plain text message
    message = f"""
Dear {patient_name},

This is a reminder that you have an appointment scheduled for tomorrow.

Appointment Details:
- Doctor: {doctor_name} ({doctor_specialty})
- Date: {appointment_date.strftime('%B %d, %Y')} ({appointment_date.strftime('%A')})
- Time: {appointment_time}
- Reason: {appointment.reason}

Please arrive 15 minutes before your scheduled appointment time.
If you need to cancel or reschedule, please contact the clinic at least 24 hours in advance.

Thank you for choosing ClinicOS.

Best regards,
The ClinicOS Team
"""
    
    # HTML message
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; margin: 0; padding: 0; background-color: #f8fafc;">
    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b5fc0 100%); padding: 40px 32px; text-align: center;">
                <div style="width: 64px; height: 64px; border-radius: 50%; background: rgba(255,255,255,0.15); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                        <line x1="16" y1="2" x2="16" y2="6"/>
                        <line x1="8" y1="2" x2="8" y2="6"/>
                        <line x1="3" y1="10" x2="21" y2="10"/>
                    </svg>
                </div>
                <h1 style="color: white; margin: 0; font-size: 1.75rem; font-weight: 700;">Appointment Reminder</h1>
                <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 1rem;">You have an appointment tomorrow</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 40px 32px;">
                <p style="font-size: 1.1rem; color: #334155; margin-bottom: 24px;">Dear <strong>{patient_name}</strong>,</p>
                
                <p style="color: #475569; font-size: 1rem; margin-bottom: 24px;">
                    This is a friendly reminder that you have an appointment scheduled for <strong>tomorrow</strong>.
                </p>
                
                <!-- Appointment Details Card -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                    <h3 style="margin: 0 0 20px; font-size: 1.1rem; font-weight: 700; color: #1e3a8a; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px;">Appointment Details</h3>
                    
                    <div style="display: grid; gap: 16px;">
                        <div>
                            <p style="margin: 0; font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Doctor</p>
                            <p style="margin: 4px 0 0; font-size: 1.1rem; font-weight: 600; color: #1e293b;">{doctor_name}</p>
                            <p style="margin: 2px 0 0; font-size: 0.9rem; color: #64748b;">{doctor_specialty}</p>
                        </div>
                        
                        <div>
                            <p style="margin: 0; font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Date</p>
                            <p style="margin: 4px 0 0; font-size: 1.1rem; font-weight: 600; color: #1e293b;">{appointment_date.strftime('%B %d, %Y')}</p>
                            <p style="margin: 2px 0 0; font-size: 0.9rem; color: #64748b;">{appointment_date.strftime('%A')}</p>
                        </div>
                        
                        <div>
                            <p style="margin: 0; font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Time</p>
                            <p style="margin: 4px 0 0; font-size: 1.1rem; font-weight: 600; color: #1e293b;">{appointment_time}</p>
                        </div>
                        
                        <div>
                            <p style="margin: 0; font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Reason</p>
                            <p style="margin: 4px 0 0; font-size: 1rem; color: #334155;">{appointment.reason}</p>
                        </div>
                    </div>
                </div>
                
                <!-- Important Notes -->
                <div style="background: #fefce8; border: 1px solid #fde68a; border-radius: 12px; padding: 16px; margin-bottom: 24px;">
                    <p style="margin: 0 0 8px; font-weight: 600; color: #92400e; font-size: 0.95rem;">Important Reminders:</p>
                    <ul style="margin: 0; padding-left: 20px; color: #92400e; font-size: 0.9rem; line-height: 1.7;">
                        <li>Please arrive <strong>15 minutes early</strong> for check-in</li>
                        <li>Bring your <strong>ID and insurance card</strong></li>
                        <li>To cancel or reschedule, contact us at least <strong>24 hours in advance</strong></li>
                    </ul>
                </div>
                
                <p style="color: #64748b; font-size: 0.95rem; text-align: center; margin-top: 32px;">
                    Thank you for choosing <strong>ClinicOS</strong>
                </p>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; padding: 24px 32px 0; border-top: 1px solid #e2e8f0; margin-top: 24px;">
                <p style="margin: 0; font-size: 0.85rem; color: #94a3b8;">The ClinicOS Team</p>
                <p style="margin: 8px 0 0; font-size: 0.75rem; color: #94a3b8;">This is an automated reminder. Please do not reply to this email.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send appointment reminder email: {e}")
        return False


def send_medication_reminder_email(medication, reminder_time=None):
    """
    Send medication reminder email to patient at exact time.
    """
    patient = medication.patient
    patient_email = patient.email
    patient_name = patient.full_name
    med_name = medication.name
    dosage = medication.dosage
    
    # Get all scheduled times for this medication
    times_list = []
    if medication.times_of_day:
        times_list = [t.strip() for t in medication.times_of_day.split(',') if t.strip()]
    else:
        times_list = [str(medication.time)]
    
    # If reminder_time is provided, use that specific time
    if reminder_time:
        current_time_str = reminder_time.strftime('%H:%M')
        times_display = current_time_str
    else:
        times_display = ', '.join(times_list)
    
    subject = f'Medication Reminder: {medication.name} ({medication.dosage})'
    
    # Plain text message
    message = f"""
Dear {patient.full_name},

This is a reminder to take your medication.

Medication Details:
- Medication: {medication.name}
- Dosage: {medication.dosage}
- Time: {reminder_time.strftime('%H:%M') if reminder_time else ', '.join(times_list)}

Please take your medication as prescribed by your doctor.

Best regards,
The ClinicOS Team
"""
    
    # HTML message
    html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; margin: 0; padding: 0; background-color: #f8fafc;">
    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #ea580c 0%, #f97316 100%); padding: 40px 32px; text-align: center;">
                <div style="width: 64px; height: 64px; border-radius: 50%; background: rgba(255,255,255,0.15); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                        <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
                        <line x1="12" y1="9" x2="12" y2="15" stroke-linecap="round"/>
                        <circle cx="12" cy="12" r="3" fill="currentColor" opacity="0.15"/>
                    </svg>
                </div>
                <h1 style="color: white; margin: 0; font-size: 1.75rem; font-weight: 700;">Medication Reminder</h1>
                <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 1rem;">Time to take your medication</p>
            </div>
            
            <div style="padding: 40px 32px;">
                <p style="font-size: 1.1rem; color: #334155; margin-bottom: 24px;">Dear <strong>{patient.full_name}</strong>,</p>
                
                <p style="color: #475569; font-size: 1rem; margin-bottom: 24px;">
                    This is a reminder to take your medication as prescribed.
                </p>
                
                <div style="background: #fff7ed; border: 1px solid #fed7aa; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                    <h3 style="margin: 0 0 20px; font-size: 1.1rem; font-weight: 700; color: #92400e; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px;">Medication Details</h3>
                    
                    <div style="display: grid; gap: 16px;">
                        <div>
                            <p style="margin: 0; font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Medication</p>
                            <p style="margin: 4px 0 0; font-size: 1.1rem; font-weight: 600; color: #1e293b;">{medication.name}</p>
                        </div>
                        <div>
                            <p style="margin: 0; font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Dosage</p>
                            <p style="margin: 4px 0 0; font-size: 1.1rem; font-weight: 600; color: #1e293b;">{medication.dosage}</p>
                        </div>
                        <div>
                            <p style="margin: 0; font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Time</p>
                            <p style="margin: 4px 0 0; font-size: 1.1rem; font-weight: 600; color: #1e293b;">{reminder_time.strftime('%H:%M') if reminder_time else ', '.join(times_list)}</p>
                        </div>
                    </div>
                </div>
                
                <!-- Important Notes -->
                <div style="background: #fefce8; border: 1px solid #fde68a; border-radius: 12px; padding: 16px; margin-bottom: 24px;">
                    <p style="margin: 0 0 8px; font-weight: 600; color: #92400e; font-size: 0.95rem;">Important Reminders:</p>
                    <ul style="margin: 0; padding-left: 20px; color: #92400e; font-size: 0.9rem; line-height: 1.7;">
                        <li>Take medication exactly as prescribed</li>
                        <li>Do not skip doses without consulting your doctor</li>
                        <li>Contact your doctor if you experience side effects</li>
                    </ul>
                </div>
                
                <p style="color: #64748b; font-size: 0.95rem; text-align: center; margin-top: 32px;">
                    Thank you for choosing <strong>ClinicOS</strong>
                </p>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; padding: 24px 32px 0; border-top: 1px solid #e2e8f0; margin-top: 24px;">
                <p style="margin: 0; font-size: 0.85rem; color: #94a3b8;">The ClinicOS Team</p>
                <p style="margin: 8px 0 0; font-size: 0.75rem; color: #94a3b8;">This is an automated reminder. Please do not reply to this email.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send medication reminder email: {e}")
        return False


def send_appointment_reminders_for_tomorrow():
    """
    Send reminder emails for all appointments scheduled for tomorrow.
    This should be run daily via a cron job or scheduled task.
    """
    tomorrow = date.today() + timedelta(days=1)
    
    appointments = Appointment.objects.filter(
        day=tomorrow.day,
        month=tomorrow.month,
        year=tomorrow.year,
        is_cancelled=False
    ).select_related('patient', 'doctor')
    
    sent_count = 0
    failed_count = 0
    
    for appointment in appointments:
        if send_appointment_reminder_email(appointment):
            sent_count += 1
        else:
            failed_count += 1
    
    return {
        'total': sent_count + failed_count,
        'sent': sent_count,
        'failed': failed_count,
        'date': tomorrow,
    }


def send_medication_reminders_for_current_time():
    """
    Send medication reminder emails for medications due at the current time.
    This should be run every 15 minutes via a cron job or scheduled task.
    """
    now = datetime.now()
    current_time = now.time()
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    # Round to nearest 15 minutes for matching
    # We check if current time matches any medication time within a 7-minute window
    weekday_map = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'}
    today_name = weekday_map[date.today().weekday()]
    
    # Get all medications for today
    medications = Medication.objects.filter(
        days_of_week__contains=today_name
    ).select_related('patient')
    
    sent_count = 0
    failed_count = 0
    
    for medication in medications:
        # Get all scheduled times for this medication
        times_list = []
        if medication.times_of_day:
            times_list = [t.strip() for t in medication.times_of_day.split(',') if t.strip()]
        else:
            times_list = [str(medication.time)]
        
        # Check if current time matches any scheduled time (within 7 minutes)
        for time_str in times_list:
            try:
                med_time = datetime.strptime(time_str, '%H:%M').time()
                # Check if current time is within 7 minutes of medication time
                med_datetime = datetime.combine(date.today(), med_time)
                current_datetime = datetime.combine(date.today(), current_time)
                diff_minutes = abs((current_datetime - med_datetime).total_seconds() / 60)
                
                if diff_minutes <= 7:  # Within 7 minutes window
                    if send_medication_reminder_email(medication, reminder_time=current_time):
                        sent_count += 1
                    else:
                        failed_count += 1
                    break  # Only send once per medication per check
            except ValueError:
                continue
    
    return {
        'total': sent_count + failed_count,
        'sent': sent_count,
        'failed': failed_count,
        'date': date.today(),
    }


def send_appointment_reminders_for_tomorrow():
    """
    Send reminder emails for all appointments scheduled for tomorrow.
    This should be run daily via a cron job or scheduled task.
    """
    tomorrow = date.today() + timedelta(days=1)
    
    appointments = Appointment.objects.filter(
        day=tomorrow.day,
        month=tomorrow.month,
        year=tomorrow.year,
        is_cancelled=False
    ).select_related('patient', 'doctor')
    
    sent_count = 0
    failed_count = 0
    
    for appointment in appointments:
        if send_appointment_reminder_email(appointment):
            sent_count += 1
        else:
            failed_count += 1
    
    return {
        'total': sent_count + failed_count,
        'sent': sent_count,
        'failed': failed_count,
        'date': tomorrow,
    }


def send_doctor_patient_list_for_tomorrow():
    """
    Send doctor's patient list for tomorrow's appointments.
    This should be run daily in the evening (e.g., 8 PM) via a cron job.
    Sends each doctor a list of their patients for tomorrow with 2-line summary per patient.
    """
    tomorrow = date.today() + timedelta(days=1)
    
    appointments = Appointment.objects.filter(
        day=tomorrow.day,
        month=tomorrow.month,
        year=tomorrow.year,
        is_cancelled=False
    ).select_related('patient', 'doctor').order_by('doctor', 'hour', 'minute')
    
    # Group appointments by doctor
    from collections import defaultdict
    doctor_appointments = defaultdict(list)
    
    for appt in appointments:
        doctor_appointments[appt.doctor].append(appt)
    
    sent_count = 0
    failed_count = 0
    
    for doctor, appointments_list in doctor_appointments.items():
        if not doctor.user.email:
            continue
            
        subject = f'Patient List for Tomorrow ({tomorrow.strftime("%B %d, %Y")}) - Dr. {doctor.name}'
        
        # Build patient list (2 lines per patient)
        patient_lines = []
        for appt in appointments_list:
            patient = appt.patient
            line1 = f"{appt.hour:02d}:{appt.minute:02d} - {patient.full_name}"
            line2 = f"  Age: {patient.age}, Phone: {patient.phone}, Reason: {appt.reason}"
            patient_lines.append(f"{line1}\n{line2}")
        
        patient_list_text = "\n\n".join(patient_lines)
        
        # Plain text message
        message = f"""
Dear Dr. {doctor.name},

Here is your patient list for tomorrow ({tomorrow.strftime('%A, %B %d, %Y')}):

{patient_list_text}

Total patients: {len(appointments_list)}

Best regards,
ClinicOS
"""
        
        # HTML message
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; margin: 0; padding: 0; background-color: #f8fafc;">
    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b5fc0 100%); padding: 40px 32px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 1.75rem; font-weight: 700;">Tomorrow's Patient List</h1>
                <p style="color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 1rem;">Dr. {doctor.name} - {tomorrow.strftime('%A, %B %d, %Y')}</p>
            </div>
            
            <div style="padding: 40px 32px;">
                <p style="font-size: 1.1rem; color: #334155; margin-bottom: 24px;">Dear Dr. <strong>{doctor.name}</strong>,</p>
                
                <p style="color: #475569; font-size: 1rem; margin-bottom: 24px;">
                    Here is your patient list for <strong>tomorrow ({tomorrow.strftime('%A, %B %d, %Y')})</strong>.
                </p>
                
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                    <h3 style="margin: 0 0 20px; font-size: 1.1rem; font-weight: 700; color: #1e3a8a; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px;">Patients ({len(appointments_list)} total)</h3>
                    
                    <div style="font-family: monospace; font-size: 0.9rem; line-height: 1.8; white-space: pre-wrap; color: #334155;">
{chr(10).join(patient_lines)}
                    </div>
                </div>
                
                <p style="color: #64748b; font-size: 0.95rem; text-align: center; margin-top: 32px;">
                    Thank you for choosing <strong>ClinicOS</strong>
                </p>
            </div>
            
            <!-- Footer -->
            <div style="text-align: center; padding: 24px 32px 0; border-top: 1px solid #e2e8f0; margin-top: 24px;">
                <p style="margin: 0; font-size: 0.85rem; color: #94a3b8;">The ClinicOS Team</p>
                <p style="margin: 8px 0 0; font-size: 0.75rem; color: #94a3b8;">This is an automated summary. Please do not reply to this email.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[doctor.user.email],
                html_message=html_message,
                fail_silently=False,
            )
            sent_count += 1
        except Exception as e:
            print(f"Failed to send doctor patient list email to Dr. {doctor.name}: {e}")
            failed_count += 1
    
    return {
        'total': sent_count + failed_count,
        'sent': sent_count,
        'failed': failed_count,
        'date': tomorrow,
    }