"""
ClinicOS Telegram bot.

Delivers reminders over Telegram (free, worldwide). Patients receive medication
and appointment reminders; doctors receive their patient list at 10 PM.

Users connect their Telegram account by opening a deep link:
    https://t.me/<bot_username>?start=<one_time_token>
Telegram sends that to the bot as "/start <token>". The webhook endpoint
(accounts/views.py telegram_webhook) calls handle_update(); we match the token
to a ClinicOS user and remember their chat_id so the scheduler can message them.

Everything is best-effort: if the token isn't configured (or a send fails) the
rest of the app keeps working.
"""
import json
import logging
import os
import secrets
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger('accounts')

TELEGRAM_API = 'https://api.telegram.org/bot{token}/{method}'


def bot_enabled():
    return bool(settings.TELEGRAM_BOT_TOKEN)


def api_call(method, payload=None):
    """Call the Telegram Bot API. Returns parsed JSON, or {'ok': False, ...} on error."""
    import urllib.request
    import urllib.parse
    import urllib.error

    if not bot_enabled():
        return {'ok': False, 'error': 'TELEGRAM_BOT_TOKEN not configured'}
    url = TELEGRAM_API.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)
    data = urllib.parse.urlencode(payload or {}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        logger.warning('Telegram %s HTTP %s: %s', method, e.code, body)
        return {'ok': False, 'error': f'HTTP {e.code}', 'body': body}
    except Exception as e:
        logger.warning('Telegram %s error: %s', method, e)
        return {'ok': False, 'error': str(e)}


def send_message(chat_id, text):
    """Send a plain-text message to a chat_id. Best-effort."""
    if not chat_id or not text:
        return {'ok': False, 'error': 'missing chat_id or text'}
    return api_call('sendMessage', {
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': True,
    })


def get_me():
    """Current bot identity from Telegram (cached per process)."""
    if not bot_enabled():
        return {}
    if getattr(get_me, '_cache', None):
        return get_me._cache
    res = api_call('getMe', {})
    info = res.get('result') or {}
    get_me._cache = info
    return info


def bot_link(extra=None):
    """Deep link like https://t.me/BotUsername?start=TOKEN (blank if unconfigured)."""
    username = (settings.TELEGRAM_BOT_USERNAME or '').strip().lstrip('@')
    if not username:
        username = (get_me().get('username') or '').strip().lstrip('@')
    if not username:
        return ''
    return f'https://t.me/{username}' + (f'?start={extra}' if extra else '')


def generate_link_token(user):
    """Create a fresh one-time link token for a user (idempotent per call)."""
    token = secrets.token_urlsafe(24)
    user.telegram_link_token = token
    user.save(update_fields=['telegram_link_token'])
    return token


def set_webhook(url):
    """Register our HTTPS endpoint as the bot's webhook."""
    return api_call('setWebhook', {'url': url, 'drop_pending_updates': True})


def webhook_url(request=None, base=None):
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    base = base or settings.TELEGRAM_WEBHOOK_BASE or os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
    if base:
        if not base.startswith('http'):
            base = 'https://' + base
        return f'{base.rstrip("/")}/telegram/webhook/{secret}/'
    if request is not None:
        return request.build_absolute_uri(f'/telegram/webhook/{secret}/')
    return ''


def _linked_user(chat_id):
    User = get_user_model()
    return User.objects.filter(telegram_chat_id=str(chat_id)).first()


_WEEKDAY_NAMES = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday',
                  4: 'friday', 5: 'saturday', 6: 'sunday'}


def _patient_of(user):
    try:
        return user.patient_profile
    except Exception:
        return None


def _doctor_of(user):
    try:
        return user.doctor_profile
    except Exception:
        return None


def _welcome_for(user):
    role = user.role or 'patient'
    if role == 'doctor':
        return (
            f"✅ Connected to ClinicOS as {user.username} (Doctor).\n"
            f"From now on you'll receive your patient list here every day at 10 PM.\n\n"
            f"Commands:\n"
            f"• /today — today's patient list\n"
            f"• /tomorrow — tomorrow's patient list\n"
            f"• /appointments — your upcoming schedule\n"
            f"• /help — show this message"
        )
    if role == 'admin':
        return (
            f"✅ Connected to ClinicOS as {user.username} (Admin).\n\n"
            f"Commands:\n"
            f"• /today, /tomorrow — patient lists (doctors)\n"
            f"• /appointments — upcoming appointments\n"
            f"• /help — show this message"
        )
    return (
        f"✅ Connected to ClinicOS as {user.username} (Patient).\n"
        f"From now on you'll receive your reminders here: "
        f"medication times and the day before each appointment.\n\n"
        f"Commands:\n"
        f"• /medications — your medication schedule\n"
        f"• /appointments — your upcoming appointments\n"
        f"• /next — your next appointment\n"
        f"• /help — show this message"
    )


def _help_for(user):
    role = user.role or 'patient'
    if role == 'doctor':
        return (
            "ClinicOS Doctor Commands:\n"
            "• /today — today's patient list\n"
            "• /tomorrow — tomorrow's patient list\n"
            "• /appointments — your upcoming schedule\n"
            "• /help — show this message\n\n"
            "Every day at 10 PM you'll also receive tomorrow's patient list automatically."
        )
    if role == 'admin':
        return (
            "ClinicOS Admin Commands:\n"
            "• /today, /tomorrow — patient lists\n"
            "• /appointments — upcoming appointments\n"
            "• /help — show this message"
        )
    return (
        "ClinicOS Patient Commands:\n"
        "• /medications — your medication schedule\n"
        "• /appointments — your upcoming appointments\n"
        "• /next — your next appointment\n"
        "• /help — show this message\n\n"
        "You'll also be reminded automatically: medication times and the day before each appointment."
    )


def _format_appointment(appt):
    d = appt.doctor
    return (
        f"• {date(appt.year, appt.month, appt.day).strftime('%a, %b %d')} "
        f"{appt.hour:02d}:{appt.minute:02d} — Dr. {d.name} ({d.specialty})"
        + (f" — {appt.reason}" if appt.reason else "")
    )


def _format_patient_line(appt):
    p = appt.patient
    return (
        f"• {appt.hour:02d}:{appt.minute:02d} — {p.full_name} "
        f"(age {p.age}, {p.phone}) — {appt.reason}"
    )


def _upcoming_appointments(qs, today):
    return [
        a for a in qs.order_by('year', 'month', 'day', 'hour', 'minute')
        if date(a.year, a.month, a.day) >= today
    ]


def handle_update(update):
    """
    Process a single Telegram update (a message). Returns a dict describing
    what happened, for the caller (view) to act on.
    """
    if not bot_enabled():
        return {'ok': False, 'error': 'bot not configured'}

    message = update.get('message')
    if not message:
        # Callback queries / edited messages: ignore for now.
        return {'ok': True, 'action': 'ignored'}

    chat = message.get('chat') or {}
    chat_id = chat.get('id')
    text = message.get('text') or ''
    user_name = chat.get('username') or chat.get('first_name') or ''

    # Resolve bot identity once
    me = get_me()
    bot_username = (me.get('username') or 'ClinicOSBot').lstrip('@')
    deep_link = f'https://t.me/{bot_username}?start='

    if not text.startswith('/'):
        # Any non-command message: acknowledge and show a hint for the linked role.
        user = _linked_user(chat_id)
        if user and user.role == 'doctor':
            send_message(chat_id, 'Doctor menu: send /today for today\u2019s patients, /tomorrow for tomorrow\u2019s, or /help.')
        elif user:
            send_message(chat_id, 'Your menu: send /medications, /appointments, or /next. Or /help for all commands.')
        else:
            send_message(chat_id, 'ClinicOS bot is connected. Use the Connect link on the ClinicOS website to link your account, then /help.')
        return {'ok': True, 'action': 'ack'}

    parts = text.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == '/start':
        token = args[0] if args else ''
        User = get_user_model()

        if token:
            user = User.objects.filter(telegram_link_token=token).first()
            if user is None:
                send_message(chat_id, 'This link is not valid or has expired. Open the "Connect" button on the ClinicOS website.')
                return {'ok': False, 'action': 'invalid_token'}
            user.telegram_chat_id = str(chat_id)
            user.telegram_link_token = None
            user.save(update_fields=['telegram_chat_id', 'telegram_link_token'])
            send_message(chat_id, _welcome_for(user))
            return {'ok': True, 'action': 'linked', 'user': user.username}

        # No token: show connection instructions (role-specific once linked)
        help_text = (
            f"Welcome to the ClinicOS bot!\n\n"
            f"To link your ClinicOS account, open the Connect (blue paper-plane) "
            f"button on the ClinicOS website while logged in — or use this deep link:\n"
            f"{deep_link}<your-token>\n\n"
            f"Once connected you'll get:\n"
            f"• 💊 Medication reminders at take-time (patients)\n"
            f"• 📅 Appointment reminders the day before (patients)\n"
            f"• 📋 Your daily patient list at 10 PM (doctors)\n\n"
            f"Then send /help to see your commands."
        )
        send_message(chat_id, help_text)
        return {'ok': True, 'action': 'started'}

    if cmd in ('/help',):
        user = _linked_user(chat_id)
        if user:
            send_message(chat_id, _help_for(user))
        else:
            send_message(chat_id, (
                "ClinicOS bot is connected.\n"
                f"To get your personal reminders, open the Connect link on the "
                f"ClinicOS website while logged in (or use {deep_link}<your-token>), "
                f"then send /help to see your commands."
            ))
        return {'ok': True, 'action': 'help'}

    # ---------------- Patient commands ----------------
    if cmd in ('/medications', '/appointments', '/next'):
        user = _linked_user(chat_id)
        if not user:
            send_message(chat_id, 'Your Telegram is not connected to a ClinicOS account. Use the Connect button on the website.')
            return {'ok': False, 'action': 'not_linked'}
        patient = _patient_of(user)
        if not patient:
            send_message(chat_id, 'This account is not a patient. Doctors use /today and /tomorrow for patient lists.')
            return {'ok': False, 'action': 'not_patient'}

        from accounts.email_utils import _clinic_today
        from accounts.models import Appointment, Medication

        today = _clinic_today()

        if cmd == '/medications':
            today_name = _WEEKDAY_NAMES.get(today.weekday(), '')
            applicable = []
            for med in Medication.objects.filter(patient=patient):
                if med.days_of_week:
                    med_days = [d.strip().lower() for d in med.days_of_week.split(',') if d.strip()]
                    if today_name in med_days:
                        applicable.append(med)
                elif (med.day == today.day and med.month == today.month
                        and med.year == today.year):
                    applicable.append(med)
            applicable.sort(key=lambda m: m.time)

            if not applicable:
                send_message(chat_id, f'You have no medications scheduled for today ({today.strftime("%A, %b %d")}).')
                return {'ok': True, 'action': 'meds_sent'}

            lines = [f"💊 Your medications for {today.strftime('%A, %b %d')}:"]
            for med in applicable:
                lines.append(f"• {med.name} ({med.dosage}) — {med.get_times_display()}")
            send_message(chat_id, "\n".join(lines))
            return {'ok': True, 'action': 'meds_sent'}

        upcoming = _upcoming_appointments(
            Appointment.objects.filter(patient=patient, is_cancelled=False), today
        )

        if cmd == '/next':
            if not upcoming:
                send_message(chat_id, 'You have no upcoming appointments. Contact the clinic to book one.')
                return {'ok': True, 'action': 'empty_appointments'}
            msg = "📅 Your next appointment:\n" + _format_appointment(upcoming[0])
            send_message(chat_id, msg)
            return {'ok': True, 'action': 'appointments_sent'}

        if not upcoming:
            send_message(chat_id, 'You have no upcoming appointments. Contact the clinic to book one.')
            return {'ok': True, 'action': 'empty_appointments'}
        lines = ["📅 Your upcoming appointments:"] + [_format_appointment(a) for a in upcoming[:6]]
        send_message(chat_id, "\n".join(lines))
        return {'ok': True, 'action': 'appointments_sent'}

    # ---------------- Doctor commands ----------------
    if cmd in ('/today', '/list', '/patients', '/tomorrow'):
        user = _linked_user(chat_id)
        if not user:
            send_message(chat_id, 'Your Telegram is not connected to a ClinicOS account. Use the Connect button on the website.')
            return {'ok': False, 'action': 'not_linked'}
        doctor = _doctor_of(user)
        if not doctor:
            send_message(chat_id, 'Only doctors can request the patient list. Use the Connect button on the website.')
            return {'ok': False, 'action': 'not_doctor'}

        from datetime import timedelta
        from accounts.email_utils import _clinic_today
        from accounts.models import Appointment
        target = _clinic_today() + (timedelta(days=1) if cmd == '/tomorrow' else timedelta(days=0))
        appointments = Appointment.objects.filter(
            doctor=doctor,
            day=target.day,
            month=target.month,
            year=target.year,
            is_cancelled=False
        ).order_by('hour', 'minute')

        if not appointments:
            hint = (' Send /today to see today\u2019s list.' if cmd == '/tomorrow'
                    else ' Send /tomorrow to see tomorrow\u2019s list.')
            send_message(chat_id, f'No appointments for {target.strftime("%A, %b %d")}.{hint}')
            return {'ok': True, 'action': 'empty_list'}

        lines = [f"📋 Your patient list for {target.strftime('%A, %b %d')}:"]
        lines += [_format_patient_line(a) for a in appointments]
        lines.append(f"\nTotal: {len(appointments)} patient(s)")
        send_message(chat_id, "\n".join(lines))
        return {'ok': True, 'action': 'list_sent'}

    # ---------------- Shared: upcoming appointments (doctor schedule or patient) ----------------
    if cmd == '/appointments':
        user = _linked_user(chat_id)
        if not user:
            send_message(chat_id, 'Your Telegram is not connected to a ClinicOS account. Use the Connect button on the website.')
            return {'ok': False, 'action': 'not_linked'}
        doctor = _doctor_of(user)
        patient = _patient_of(user)
        if not (doctor or patient):
            send_message(chat_id, 'No patient or doctor profile is linked to this account yet.')
            return {'ok': False, 'action': 'no_profile'}

        from accounts.email_utils import _clinic_today
        from accounts.models import Appointment
        today = _clinic_today()
        qs = (Appointment.objects.filter(doctor=doctor) if doctor
              else Appointment.objects.filter(patient=patient))
        upcoming = _upcoming_appointments(qs.filter(is_cancelled=False), today)

        if not upcoming:
            send_message(chat_id, 'You have no upcoming appointments on your schedule.')
            return {'ok': True, 'action': 'empty_appointments'}
        lines = ["📅 Upcoming appointments:"] + [_format_appointment(a) for a in upcoming[:6]]
        send_message(chat_id, "\n".join(lines))
        return {'ok': True, 'action': 'appointments_sent'}

    # Unknown/unsupported command
    user = _linked_user(chat_id)
    if user and user.role == 'doctor':
        send_message(chat_id, f'Unknown command: {cmd}. Send /help to see your commands, or /today for today\u2019s patient list.')
    elif user:
        send_message(chat_id, f'Unknown command: {cmd}. Send /help to see your commands, or /medications for today\u2019s medicines.')
    else:
        send_message(chat_id, f'Unknown command: {cmd}. Use the Connect link on the ClinicOS website to link your account, then /help.')
    return {'ok': True, 'action': 'unknown'}


def bot_status():
    """Read-only status for the diagnostics page (no secrets). Includes a live
    check against api.telegram.org when the token is configured."""
    if not bot_enabled():
        return {'enabled': False, 'detail': 'Telegram bot disabled (set TELEGRAM_BOT_TOKEN).'}

    identity = get_me()
    username = (settings.TELEGRAM_BOT_USERNAME or identity.get('username') or '').strip().lstrip('@')
    webhook = api_call('getWebhookInfo', {})
    webhook_ok = bool((webhook.get('result') or {}).get('url'))

    detail = 'Telegram bot ready and reachable.'
    if not username:
        detail = 'Token configured but bot username could not be determined (getMe failed or Telegram unreachable).'
    if not webhook_ok:
        detail += ' Webhook not registered (users can still connect via the site link).'

    return {
        'enabled': True,
        'detail': detail,
        'bot_username': username or None,
        'bot_username_set': bool(username),
        'bot_name': settings.TELEGRAM_BOT_NAME,
        'bot_first_name': identity.get('first_name') or None,
        'webhook_set': webhook_ok,
        'webhook_url': (webhook.get('result') or {}).get('url') or None,
        'computed_webhook_url': webhook_url(),
    }


BOT_BIO = (
    "ClinicOS bot - your clinic companion.\n\n"
    "Patients receive medication reminders at the right time and a heads-up "
    "the day before each appointment. Doctors receive their patient list every "
    "day at 10 PM with the patient's name, appointment time, phone, and reason.\n\n"
    "Just press Start and connect using the link on the ClinicOS website "
    "to begin receiving your reminders."
)

BOT_SHORT_BIO = "ClinicOS reminders: medications, appointments, and doctor patient lists."

BOT_COMMANDS = [
    ('start', 'Connect your ClinicOS account'),
    ('help', 'Show your commands'),
    ('medications', 'Your medication schedule (patients)'),
    ('appointments', 'Upcoming appointments'),
    ('next', 'Your next appointment (patients)'),
    ('today', "Today's patient list (doctors)"),
    ('tomorrow', "Tomorrow's patient list (doctors)"),
]


def configure_bot():
    """
    Apply the professional bot settings (name, bio, commands) and register the
    webhook using the server's native fallback (RAILWAY_PUBLIC_DOMAIN etc).
    Runs from the server (which can reach api.telegram.org).
    """
    if not bot_enabled():
        return {'ok': False, 'error': 'TELEGRAM_BOT_TOKEN not configured'}
    results = {}

    results['setMyName'] = api_call('setMyName', {'name': settings.TELEGRAM_BOT_NAME})
    results['setMyDescription'] = api_call('setMyDescription', {'description': BOT_BIO})
    results['setMyShortDescription'] = api_call('setMyShortDescription', {'short_description': BOT_SHORT_BIO})
    results['setMyCommands'] = api_call('setMyCommands', {'commands': json.dumps([
        {'command': c, 'description': d} for c, d in BOT_COMMANDS
    ])})

    url = webhook_url()  # uses the server's native fallback (RAILWAY_PUBLIC_DOMAIN)
    if url:
        results['setWebhook'] = set_webhook(url)
    else:
        results['setWebhook'] = {'ok': False, 'error': 'no base URL available'}

    return {'ok': True, 'results': results}