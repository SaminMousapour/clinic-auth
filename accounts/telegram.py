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
        # Any non-command message: acknowledge and show hint.
        send_message(chat_id, 'ClinicOS bot is connected. Send /start to see options, /help for commands.')
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
            user.telegram_link_token = ''
            user.save(update_fields=['telegram_chat_id', 'telegram_link_token'])

            role_label = dict(user.ROLE_CHOICES).get(user.role, 'user')
            welcome = (
                f"✅ Connected to ClinicOS as {user.username} ({role_label}).\n"
                f"From now on you'll get your reminders here: "
                f"medication times, your appointments, and (if you're a doctor) your patient list at 10 PM.\n\n"
                f"Commands:\n"
                f"• /list — today's patient list (doctors)\n"
                f"• /help — show this message"
            )
            send_message(chat_id, welcome)
            return {'ok': True, 'action': 'linked', 'user': user.username}

        # No token: show help with dynamic deep link
        help_text = (
            f"Welcome to the ClinicOS bot!\n\n"
            f"To get reminders with your ClinicOS account, "
            f"open the Connect link on the ClinicOS website while logged in "
            f"(or use this deep link):\n{deep_link}<your-token>\n\n"
            f"This bot can send you:\n"
            f"• 💊 Medication reminders at take-time\n"
            f"• 📅 Appointment reminders (day before, at 10 PM)\n"
            f"• 📋 Patient list for doctors (10 PM daily)\n\n"
            f"Commands:\n"
            f"• /list — today's patient list (doctors)\n"
            f"• /help — show this message"
        )
        send_message(chat_id, help_text)
        return {'ok': True, 'action': 'started'}

    if cmd in ('/help',):
        help_text = (
            f"ClinicOS Bot Commands:\n"
            f"• /start — connect your account (use deep link from website)\n"
            f"• /list — today's patient list (doctors only)\n"
            f"• /help — show this message"
        )
        send_message(chat_id, help_text)
        return {'ok': True, 'action': 'help'}

    if cmd in ('/list', '/patients', '/today'):
        User = get_user_model()
        user = User.objects.filter(telegram_chat_id=str(chat_id)).first()
        if not user:
            send_message(chat_id, 'Your Telegram is not connected to a ClinicOS account. Use the Connect button on the website.')
            return {'ok': False, 'action': 'not_linked'}

        if user.role != 'doctor':
            send_message(chat_id, 'Only doctors can request the patient list. Patients receive reminders automatically.')
            return {'ok': False, 'action': 'not_doctor'}

        # Fetch today's appointments for this doctor
        try:
            doctor = user.doctor_profile
        except Exception:
            send_message(chat_id, 'Doctor profile not found.')
            return {'ok': False, 'action': 'no_doctor_profile'}

        from accounts.email_utils import _clinic_today
        from accounts.models import Appointment
        today = _clinic_today()
        appointments = Appointment.objects.filter(
            doctor=doctor,
            day=today.day,
            month=today.month,
            year=today.year,
            is_cancelled=False
        ).order_by('hour', 'minute')

        if not appointments:
            send_message(chat_id, f'No appointments for today ({today.strftime("%A, %b %d")}).')
            return {'ok': True, 'action': 'empty_list'}

        lines = [f"📋 Your patient list for {today.strftime('%A, %b %d')}:"]
        for appt in appointments:
            p = appt.patient
            lines.append(
                f"• {appt.hour:02d}:{appt.minute:02d} — {p.full_name} "
                f"(age {p.age}, {p.phone}) — {appt.reason}"
            )
        lines.append(f"\nTotal: {len(appointments)} patient(s)")
        send_message(chat_id, "\n".join(lines))
        return {'ok': True, 'action': 'list_sent'}

    # Unknown command
    send_message(chat_id, f'Unknown command: {cmd}. Send /help for options.')
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
    ('start', 'Connect your ClinicOS account and see options'),
    ('help', 'About this bot'),
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