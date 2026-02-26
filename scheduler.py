import logging
from datetime import datetime, date

from apscheduler.schedulers.background import BackgroundScheduler

from models import db, Patient, TaskLog
from notifications import send_push_notification
from translations import t, get_meal_type_name

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def generate_water_times(start_time, end_time, interval_hours):
    """Generate water reminder times between start and end."""
    times = []
    sh, sm = map(int, start_time.split(':'))
    eh, em = map(int, end_time.split(':'))
    current_minutes = sh * 60 + sm
    end_minutes = eh * 60 + em
    interval_minutes = int(interval_hours * 60)

    while current_minutes <= end_minutes:
        h, m = divmod(current_minutes, 60)
        times.append(f"{h:02d}:{m:02d}")
        current_minutes += interval_minutes

    return times


def check_and_send_reminders(app):
    """Check all patients' schedules and send reminders for current time."""
    with app.app_context():
        try:
            now = datetime.now()
            current_time = now.strftime('%H:%M')
            today = date.today()
            current_day = now.strftime('%A').lower()

            patients = Patient.query.filter(Patient.fcm_token.isnot(None)).all()

            for patient in patients:
                lang = patient.language or 'ar'

                # Check medications
                for med in patient.medications:
                    if med.specific_times and current_time in med.specific_times:
                        task_log = _get_or_create_task_log(patient.id, 'medication', med.id, current_time, today)
                        if not task_log.confirmed:
                            send_push_notification(
                                patient.fcm_token,
                                t('medication_reminder', lang),
                                t('medication_body', lang, name=med.name, dosage=med.dosage or ''),
                                data={'task_log_id': task_log.id, 'type': 'medication'}
                            )

                # Check meals
                for meal in patient.meals:
                    if meal.time == current_time:
                        task_log = _get_or_create_task_log(patient.id, 'meal', meal.id, current_time, today)
                        if not task_log.confirmed:
                            meal_name = get_meal_type_name(meal.meal_type, lang)
                            send_push_notification(
                                patient.fcm_token,
                                t('meal_reminder', lang),
                                t('meal_body', lang, meal_type=meal_name, description=meal.description or ''),
                                data={'task_log_id': task_log.id, 'type': 'meal'}
                            )

                # Check activities
                for activity in patient.activities:
                    if activity.time == current_time:
                        if activity.day_of_week == 'daily' or activity.day_of_week == current_day:
                            task_log = _get_or_create_task_log(patient.id, 'activity', activity.id, current_time, today)
                            if not task_log.confirmed:
                                send_push_notification(
                                    patient.fcm_token,
                                    t('activity_reminder', lang),
                                    t('activity_body', lang, name=activity.name),
                                    data={'task_log_id': task_log.id, 'type': 'activity'}
                                )

                # Check water reminders
                for wr in patient.water_reminders:
                    water_times = generate_water_times(wr.start_time, wr.end_time, wr.interval_hours)
                    if current_time in water_times:
                        task_log = _get_or_create_task_log(patient.id, 'water', wr.id, current_time, today)
                        if not task_log.confirmed:
                            send_push_notification(
                                patient.fcm_token,
                                t('water_reminder', lang),
                                t('water_body', lang),
                                data={'task_log_id': task_log.id, 'type': 'water'}
                            )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Scheduler error: {e}")


def _get_or_create_task_log(patient_id, task_type, task_id, scheduled_time, today):
    """Get existing or create new TaskLog entry."""
    task_log = TaskLog.query.filter_by(
        patient_id=patient_id,
        task_type=task_type,
        task_id=task_id,
        scheduled_time=scheduled_time,
        date=today,
    ).first()

    if not task_log:
        task_log = TaskLog(
            patient_id=patient_id,
            task_type=task_type,
            task_id=task_id,
            scheduled_time=scheduled_time,
            date=today,
        )
        db.session.add(task_log)
        db.session.commit()

    return task_log


def start_scheduler(app):
    """Start the APScheduler to check reminders every minute."""
    scheduler.add_job(
        check_and_send_reminders,
        'interval',
        minutes=1,
        args=[app],
        id='reminder_checker',
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started - checking reminders every minute.")
