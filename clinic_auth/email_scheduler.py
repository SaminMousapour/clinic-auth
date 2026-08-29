import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger('accounts')

_scheduler = None


def get_scheduler():
    global _scheduler
    return _scheduler


def _safe_run(name, func):
    try:
        result = func()
        if result and result.get('sent', 0) > 0:
            logger.info('EMAIL %s: %s', name, result)
    except Exception as e:
        logger.error('EMAIL %s failed: %s', name, e)


def start_email_scheduler():
    """
    Start a background scheduler inside the web process.
    Runs the reminder email jobs on time without needing external cron.
    Guarded so it only starts once.
    """
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    from django.conf import settings

    from accounts.email_utils import (
        send_medication_reminders_for_current_time,
        run_daily_ten_pm_batch,
    )

    sched = BackgroundScheduler(daemon=True)

    # Every 5 minutes: medication reminders due at the current clinic time.
    sched.add_job(
        lambda: _safe_run('medication_reminder', send_medication_reminders_for_current_time),
        'interval',
        minutes=5,
        id='medication_reminders',
        max_instances=1,
        coalesce=True,
    )

    # Daily at 10 PM clinic time: appointment reminders to patients, patient lists
    # to doctors, and the compiled admin summary. Railway blocks outbound SMTP, so
    # these go out via the Brevo HTTPS API once BREVO_API_KEY is configured.
    from apscheduler.triggers.cron import CronTrigger

    clinic_ten_pm = CronTrigger(
        hour=22, minute=0, timezone=ZoneInfo(settings.CLINIC_TIME_ZONE)
    )
    sched.add_job(
        lambda: _safe_run('daily_10pm_batch', run_daily_ten_pm_batch),
        clinic_ten_pm,
        id='daily_ten_pm_batch',
        max_instances=1,
        coalesce=True,
    )

    sched.start()
    _scheduler = sched
    logger.info('Email scheduler started (10 PM clinic-time batch + 5-min medication reminders).')

    # Register the Telegram webhook pointing at this deployment, if the bot is configured.
    from accounts.telegram import bot_enabled, set_webhook, webhook_url
    if bot_enabled():
        url = webhook_url()
        if not url:
            # Cannot compute the public base from settings alone: try the first
            # allowed host, otherwise defer (set_webhook also runs on connect).
            hosts = [h for h in list(getattr(settings, 'ALLOWED_HOSTS', [])) if h not in ('*', 'healthcheck.railway.app')]
            if hosts:
                url = f'https://{hosts[0]}/telegram/webhook/{settings.TELEGRAM_WEBHOOK_SECRET}/'
        if url:
            res = set_webhook(url)
            logger.info('Telegram webhook registration %s (%s)', res.get('ok'), res.get('error', 'ok'))
        else:
            logger.warning('Telegram webhook URL could not be determined; users can still connect via the site link.')

    return _scheduler