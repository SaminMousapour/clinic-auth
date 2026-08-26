from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=False):
        user = super().save_user(request, user, form, commit=False)
        user.role = 'patient'
        user.is_admin_user = False

        base = (user.email or user.username or 'googleuser').split('@')[0]
        username = base[:140]
        suffix = 1
        while user.__class__.objects.filter(username=username).exclude(pk=user.pk).exists():
            username = f"{base[:130]}{suffix}"
            suffix += 1
        user.username = username

        user.save()
        return user

    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_authenticated and getattr(user, 'role', '') == 'patient':
            if not hasattr(user, 'patient_profile'):
                return reverse('google_complete_profile')
        return super().get_login_redirect_url(request)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed (and before the account is connected).
        """
        from accounts.models import Doctor, Patient
        
        user = sociallogin.user
        email = user.email
        
        if not email:
            return
            
        existing_user = User.objects.filter(email=email).first()
        
        if existing_user:
            sociallogin.connect(request, existing_user)
            return
            
        if Doctor.objects.filter(user__email=email).exists():
            doctor_user = Doctor.objects.get(user__email=email).user
            sociallogin.connect(request, doctor_user)
            return
            
        if Patient.objects.filter(user__email=email).exists():
            patient_user = Patient.objects.get(user__email=email).user
            sociallogin.connect(request, patient_user)
            return

    def save_user(self, request, sociallogin, form=None):
        """
        Save the user after social login. This is called for new users.
        """
        user = super().save_user(request, sociallogin, form)
        extra_data = sociallogin.account.extra_data
        
        user.first_name = extra_data.get('given_name', '')
        user.last_name = extra_data.get('family_name', '')
        user.save()
        
        return user

    def get_login_redirect_url(self, request):
        """
        Redirect based on user role after social login.
        """
        user = request.user
        
        if not user.is_authenticated:
            return super().get_login_redirect_url(request)
            
        if user.is_admin_user or user.role == 'admin':
            return reverse('admin_panel')
        elif user.role == 'doctor':
            if hasattr(user, 'doctor_profile'):
                return reverse('doctor_appointments')
            return reverse('google_complete_doctor_profile')
        elif user.role == 'patient':
            if hasattr(user, 'patient_profile'):
                return reverse('patient_dashboard')
            return reverse('google_complete_profile')
            
        return super().get_login_redirect_url(request)