# Railway Deployment Guide for ClinicOS

## Prerequisites
1. Railway account (https://railway.app)
2. GitHub account (for repo connection)
3. Google Cloud Console project with OAuth credentials
3. Gmail account for SMTP emails

## Quick Deploy Steps

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/clinic-auth.git
git push -u origin main
```

### 2. Create Railway Project
1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect Python and use nixpacks.toml

### 3. Add PostgreSQL Database
1. In Railway dashboard, click "New" → "Database" → "PostgreSQL"
2. Railway will automatically set `DATABASE_URL` environment variable

### 4. Configure Environment Variables
Go to your service → Variables tab, add these:

```env
# Required - Django
DJANGO_SECRET_KEY=your-generated-secret-key
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=your-app.railway.app

# Google OAuth (from Google Cloud Console)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Email (Gmail SMTP)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=ClinicOS <noreply@yourdomain.com>

# Security (production)
DJANGO_SECURE_SSL_REDIRECT=1
DJANGO_SESSION_COOKIE_SECURE=1
DJANGO_CSRF_COOKIE_SECURE=1

# Optional: Custom domain
# DJANGO_ALLOWED_HOSTS=your-app.railway.app,your-custom-domain.com
# CSRF_TRUSTED_ORIGINS=https://your-app.railway.app
```

### 3. Generate DJANGO_SECRET_KEY
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Google Cloud Console Setup
1. Go to https://console.cloud.google.com
2. Create/select project → APIs & Services → Credentials
3. Create OAuth 2.0 Client ID (Web application)
4. **Authorized JavaScript origins**: `https://your-app.railway.app`
5. **Authorized redirect URIs**: `https://your-app.railway.app/accounts/google/login/callback/`
6. Copy Client ID and Secret to Railway variables

### 5. Gmail App Password
1. Enable 2FA: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use the 16-char password as `EMAIL_HOST_PASSWORD`

### 5. Custom Domain (Optional)
1. Railway → Settings → Domains → Add custom domain
2. Update `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`

## Post-Deploy Commands
Railway runs these automatically via Procfile:
- `collectstatic` - Collect static files
- `migrate` - Run database migrations
- `seed_admin` - Create admin user
- `seed_doctors` - Create default doctors
- `gunicorn` - Start web server

## Commands for Manual Runs
```bash
# Send appointment reminders (add to cron)
railway run python manage.py send_appointment_reminders

# Send medication reminders (every 15 min via cron)
railway run python manage.py send_medication_reminders_now

# Send doctor patient lists (daily at 8 PM)
railway run python manage.py send_doctor_patient_list

# Create superuser
railway run python manage.py createsuperuser

# Run migrations
railway run python manage.py migrate

# Collect static files
railway run python manage.py collectstatic --noinput
```

## Monitoring
- Railway Dashboard → Logs → View real-time logs
- Railway → Metrics → CPU, Memory, Network
- Set up alerts in Railway dashboard

## Troubleshooting

### Google OAuth "redirect_uri_mismatch"
- Check Google Console → Credentials → Authorized redirect URIs
- Must match exactly: `https://your-app.railway.app/accounts/google/login/callback/`
- No trailing slashes, exact protocol (https)

### Google OAuth "invalid_client"
- Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Railway variables
- Check Google Console → Credentials → OAuth 2.0 Client IDs

### Email not sending
- Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
- Use Gmail App Password (not regular password)
- Check EMAIL_HOST=smtp.gmail.com, EMAIL_PORT=587, EMAIL_USE_TLS=True

### Database connection issues
- Railway auto-provides DATABASE_URL for PostgreSQL
- Check `DATABASE_URL` in Variables tab
- Run `railway run python manage.py migrate` if needed

### Static files not loading
- Ensure `STATIC_ROOT = BASE_DIR / 'staticfiles'` in settings
- `collectstatic` runs automatically on deploy
- WhiteNoise serves static files in production

## Useful Railway CLI Commands
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# View logs
railway logs

# Run commands
railway run python manage.py migrate
railway run python manage.py createsuperuser

# Open shell
railway shell

# View variables
railway variables

# Deploy
railway up
```