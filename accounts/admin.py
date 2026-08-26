from django.contrib import admin
from .models import User, Doctor, Patient

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'role', 'is_admin_user']

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['name', 'medical_id', 'specialty', 'medical_number']
    list_filter = ['specialty']
    search_fields = ['name_encrypted', 'medical_id', 'specialty']
    readonly_fields = ['created_at']

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['insurance']
    readonly_fields = ['created_at']
