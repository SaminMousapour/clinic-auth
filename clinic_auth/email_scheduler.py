import logging

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

    from accounts.email_utils import (
        send_appointment_reminders_due,
        send_medication_reminders_for_current_time,
        send_doctor_patient_lists_due,
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

    # Every 5 minutes: appointment reminders exactly ~24h before.
    sched.add_job(
        lambda: _safe_run('appointment_reminder', send_appointment_reminders_due),
        'interval',
        minutes=5,
        id='appointment_reminders',
        max_instances=1,
        coalesce=True,
    )

    # Every 5 minutes: doctor patient lists ~24h before first appointment of the day.
    sched.add_job(
        lambda: _safe_run('doctor_patient_list', send_doctor_patient_lists_due),
        'interval',
        minutes=5,
        id='doctor_patient_lists',
        max_instances=1,
        coalesce=True,
    )

    sched.start()
    _scheduler = sched
    logger.info('Email scheduler started.')
    return _scheduler