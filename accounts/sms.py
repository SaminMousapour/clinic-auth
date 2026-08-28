"""
Worldwide SMS delivery for ClinicOS reminders.

The app is email-first; SMS is an additional channel for patients/doctors who
only have a phone. Multiple providers are supported so the same code works for
Iran (Kavenegar / sms.ir) and worldwide (Twilio). Configure the provider and
credentials via env vars (see clinic_auth/settings.py). When no provider is
configured, every send safely returns a "not configured" result so the rest of
the app keeps working.
"""
import logging

from django.conf import settings

logger = logging.getLogger('accounts')


def normalize_phone(raw):
    """
    Convert any input into E.164 world format (+[country][number]).
    Handles: '+989121234567', '989121234567', '09121234567' (Iran local),
    '0912 123 4567', '9121234567' (when DEFAULT_PHONE_CC is Iran 98), etc.
    Returns a clean '+...' string, or None if unparseable.
    """
    if not raw:
        return None
    digits = ''.join(ch for ch in str(raw).strip() if ch.isdigit())
    if not digits:
        return None
    if str(raw).strip().startswith('+'):
        return '+' + digits
    if digits.startswith('00'):
        digits = digits[2:]
    cc = settings.DEFAULT_PHONE_CC.strip().lstrip('+')
    cleaned = digits
    if cleaned.startswith('0') and not cleaned.startswith('0' + cc):
        cleaned = cleaned[1:]
    elif cleaned.startswith('0' + cc):
        cleaned = cleaned[1:]
    if cleaned.startswith(cc) and len(cleaned) > len(cc) + 6:
        cleaned = cleaned[len(cc):]
    if not cleaned.startswith('+'):
        cleaned = '+' + cc + cleaned
    return cleaned


def _provider_ready(name):
    cfg = {
        'twilio': bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER),
        'kavenegar': bool(settings.KAVENEGAR_API_KEY),
        'smsir': bool(settings.SMSIR_API_KEY),
    }
    return cfg.get(name, False)


def _send_twilio(to_e164, message):
    sid = settings.TWILIO_ACCOUNT_SID
    token = settings.TWILIO_AUTH_TOKEN
    try:
        import urllib.request
        import urllib.parse
        import urllib.error
        import json
        url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'
        data = urllib.parse.urlencode({
            'To': to_e164,
            'From': settings.TWILIO_FROM_NUMBER,
            'Body': message,
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        import base64
        auth = 'Basic ' + base64.b64encode(f'{sid}:{token}'.encode('utf-8')).decode('ascii')
        req.add_header('Authorization', auth)
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        return {'ok': True, 'detail': 'Twilio sent', 'sid': payload.get('sid', '')}
    except Exception as e:
        return {'ok': False, 'detail': f'Twilio error: {e}'}


def _send_kavenegar(to_e164, message):
    key = settings.KAVENEGAR_API_KEY
    sender = settings.KAVENEGAR_SENDER or '100080'
    try:
        import urllib.request
        import urllib.parse
        import urllib.error
        import json
        local = to_e164.lstrip('+')
        if local.startswith(settings.DEFAULT_PHONE_CC) and (not settings.DEFAULT_PHONE_CC or settings.DEFAULT_PHONE_CC != '98'):
            pass
        if local.startswith('98'):
            local = '0' + local[2:]
        url = f'https://api.kavenegar.com/v1/{key}/sms/send.json'
        data = urllib.parse.urlencode({
            'receptor': local,
            'sender': sender,
            'message': message,
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        ok = payload.get('return', {}).get('status') == 200
        return {'ok': ok, 'detail': 'Kavenegar sent' if ok else f'Kavenegar: {payload}', 'sid': ''}
    except Exception as e:
        return {'ok': False, 'detail': f'Kavenegar error: {e}'}


def _send_smsir(to_e164, message):
    key = settings.SMSIR_API_KEY
    sender = settings.SMSIR_SENDER or ''
    try:
        import urllib.request
        import urllib.error
        import json
        local = to_e164.lstrip('+')
        if local.startswith('98'):
            local = '0' + local[2:]
        url = 'https://api.sms.ir/v1/send/bulk'
        body = json.dumps({
            'lineNumber': sender,
            'MessageText': message,
            'Mobiles': [local],
        }).encode('utf-8')
        req = urllib.request.Request(
            url, data=body,
            headers={'Content-Type': 'application/json', 'x-api-key': key},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        return {'ok': True, 'detail': f'sms.ir sent: {payload}', 'sid': ''}
    except urllib.error.HTTPError as e:
        return {'ok': False, 'detail': f'sms.ir HTTP {e.code}: {e.read().decode("utf-8", errors="replace")}'}
    except Exception as e:
        return {'ok': False, 'detail': f'sms.ir error: {e}'}


def send_sms(to, message, provider=None):
    """
    Send an SMS reminder to a phone number. Returns
    {'ok': bool, 'detail': str, 'provider': str}.
    to may be in any common format (see normalize_phone).
    """
    provider = (provider or settings.SMS_PROVIDER or '').lower()
    to_e164 = normalize_phone(to)

    if not provider:
        return {'ok': False, 'detail': 'SMS not configured (SMS_PROVIDER not set)', 'provider': ''}
    if not to_e164:
        return {'ok': False, 'detail': f'Invalid phone number: {to}', 'provider': provider}
    if not _provider_ready(provider):
        return {'ok': False, 'detail': f'SMS provider "{provider}" configured but missing credentials', 'provider': provider}

    logger.info('Sending SMS via %s to %s', provider, to_e164)
    if provider == 'twilio':
        r = _send_twilio(to_e164, message)
    elif provider == 'kavenegar':
        r = _send_kavenegar(to_e164, message)
    elif provider == 'smsir':
        r = _send_smsir(to_e164, message)
    else:
        return {'ok': False, 'detail': f'Unknown SMS provider: {provider}', 'provider': provider}
    r['provider'] = provider
    return r


def sms_provider_status():
    """Human-readable status for the diagnostics page."""
    provider = settings.SMS_PROVIDER
    if not provider:
        return {'provider': '', 'enabled': False, 'detail': 'SMS notifications disabled (set SMS_PROVIDER).'}
    if provider in ('twilio', 'kavenegar', 'smsir') and not _provider_ready(provider):
        return {'provider': provider, 'enabled': False, 'detail': f'{provider} selected but missing credentials.'}
    return {'provider': provider, 'enabled': True, 'detail': f'{provider} ready.'}