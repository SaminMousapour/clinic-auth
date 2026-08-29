from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_patient, name='register'),
    path('google/complete/', views.google_complete_profile, name='google_complete_profile'),
    path('google/complete-doctor/', views.google_complete_doctor_profile, name='google_complete_doctor_profile'),
    path('logout/', views.logout_view, name='logout'),

    # Patient appointment URLs
    path('appointments/', views.patient_appointments, name='patient_appointments'),
    path('appointments/book/', views.appointment_book, name='appointment_book'),
    path('appointments/cancel/<int:appointment_id>/', views.appointment_cancel, name='appointment_cancel'),
    path('appointments/delete/<int:appointment_id>/', views.appointment_delete, name='appointment_delete'),

    # Doctor appointment URLs
    path('doctor/appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('doctor/insurance-settings/', views.doctor_insurance_settings, name='doctor_insurance_settings'),
    path('doctor/visit/<int:appointment_id>/', views.doctor_patient_visit, name='doctor_patient_visit'),

    # Admin URLs
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/add-doctor/', views.admin_add_doctor, name='admin_add_doctor'),
    path('admin-panel/promote/', views.admin_promote_user, name='admin_promote_user'),
    path('admin-panel/demote/', views.admin_demote_user, name='admin_demote_user'),
    path('admin-panel/remove-user/', views.admin_remove_user, name='admin_remove_user'),

    # Medication URLs
    path('medications/', views.medication_list, name='medication_list'),
    path('medications/add/', views.medication_add, name='medication_add'),
    path('medications/delete/<int:med_id>/', views.medication_delete, name='medication_delete'),
    path('medications/toggle/<int:med_id>/', views.medication_toggle_taken, name='medication_toggle_taken'),
    path('medications/by-day/', views.medication_by_day, name='medication_by_day'),

    # Health URLs
    path('health/', views.health_dashboard, name='health_dashboard'),
    path('health/add/', views.health_add, name='health_add'),
    path('health/delete/<int:reading_id>/', views.health_delete, name='health_delete'),
    path('health/chart/', views.health_chart, name='health_chart'),

    # Patient medical records
    path('records/', views.patient_records, name='patient_records'),
    path('records/add/', views.patient_record_add, name='patient_record_add'),

    # Diagnostics (read-only)
    path('__email_diagnostics/', views.email_diagnostics, name='email_diagnostics'),

    # Telegram bot
    path('telegram/connect/', views.telegram_connect, name='telegram_connect'),
    path('telegram/disconnect/', views.telegram_disconnect, name='telegram_disconnect'),
    path('telegram/webhook/<str:secret>/', views.telegram_webhook, name='telegram_webhook'),

    # Test trigger (secret token)
    path('test/doctor-list-now/', views.test_doctor_list_now, name='test_doctor_list_now'),
    path('test/seed/', views.test_seed_data, name='test_seed_data'),
    path('test/create-doctor/', views.test_create_doctor, name='test_create_doctor'),
    path('test/bot-link/', views.test_bot_link, name='test_bot_link'),
]
