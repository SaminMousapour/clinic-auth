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


def bot_link(extra=None):
    """Deep link like https://t.me/BotUsername?start=TOKEN (blank if unconfigured)."""
    username = (settings.TELEGRAM_BOT_USERNAME or '').strip().lstrip('@')
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

    if not text.startswith('/start'):
        # Any non-command message: just acknowledge.
        send_message(chat_id, 'ClinicOS bot is connected. Send /start to see options.')
        return {'ok': True, 'action': 'ack'}

    token = text[len('/start'):].strip()
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
            f"medication times, your appointments, and (if you're a doctor) your patient list at 10 PM."
        )
        send_message(chat_id, welcome)
        return {'ok': True, 'action': 'linked', 'user': user.username}

    available = []
    if 'patient' in dict(User.ROLE_CHOICES).values():
        pass
    available = [
        '💊 Medication reminders at take-time',
        '📅 Appointment reminders (day before, at 10 PM)',
        '📋 Patient list for doctors (10 PM daily)',
    ]
    send_message(
        chat_id,
        f"Welcome to the ClinicOS bot!\n\nTo get reminders with your ClinicOS account, "
        f"please open the https://t.me/{settings.TELEGRAM_BOT_USERNAME or 'ClinicOSBot'} "
        f"link from the ClinicOS website while logged in.\n\nThis bot can send you:\n"
        + "\n".join(f"• {a}" for a in available),
    )
    return {'ok': True, 'action': 'started'}


def bot_status():
    """Read-only status for the diagnostics page (no secrets)."""
    if not bot_enabled():
        return {'enabled': False, 'detail': 'Telegram bot disabled (set TELEGRAM_BOT_TOKEN).'}
    detail = 'Telegram bot ready.'
    if not settings.TELEGRAM_BOT_USERNAME:
        detail = 'Token configured but TELEGRAM_BOT_USERNAME is empty (deep links on the site are disabled).'
    return {
        'enabled': True,
        'detail': detail,
        'bot_username_set': bool(settings.TELEGRAM_BOT_USERNAME),
        'bot_name': settings.TELEGRAM_BOT_NAME,
    }