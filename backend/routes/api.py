from datetime import datetime, date, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import (db, Patient, Medication, Meal, Activity,
                    WaterReminder, Habit, Friend, TaskLog, Notification)
from scheduler import generate_water_times
from translations import t, get_meal_type_name

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/patient/login', methods=['POST'])
def patient_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    patient = Patient.query.filter_by(login_username=username).first()
    if not patient or not patient.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = create_access_token(
        identity=str(patient.id),
        additional_claims={'role': 'patient'}
    )
    return jsonify({
        'token': token,
        'patient': _patient_profile(patient),
    })


@api_bp.route('/patient/profile')
@jwt_required()
def patient_profile():
    patient = _get_current_patient()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
    return jsonify(_patient_profile(patient))


@api_bp.route('/patient/tasks/today')
@jwt_required()
def tasks_today():
    patient = _get_current_patient()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    today = date.today()
    current_day = datetime.now().strftime('%A').lower()
    lang = patient.language or 'ar'
    tasks = []

    # Medications
    for med in patient.medications:
        for time_str in (med.specific_times or []):
            task_log = _get_or_create_task_log(patient.id, 'medication', med.id, time_str, today)
            tasks.append({
                'task_log_id': task_log.id,
                'type': 'medication',
                'title': t('medication_reminder', lang),
                'description': f"{med.name} - {med.dosage or ''}",
                'time': time_str,
                'confirmed': task_log.confirmed,
                'confirmed_at': task_log.confirmed_at.isoformat() if task_log.confirmed_at else None,
                'icon': 'pill',
            })

    # Meals
    for meal in patient.meals:
        if meal.time:
            task_log = _get_or_create_task_log(patient.id, 'meal', meal.id, meal.time, today)
            meal_name = get_meal_type_name(meal.meal_type, lang)
            tasks.append({
                'task_log_id': task_log.id,
                'type': 'meal',
                'title': f"{t('meal_reminder', lang)} - {meal_name}",
                'description': meal.description or '',
                'time': meal.time,
                'confirmed': task_log.confirmed,
                'confirmed_at': task_log.confirmed_at.isoformat() if task_log.confirmed_at else None,
                'icon': 'food',
            })

    # Activities
    for activity in patient.activities:
        if activity.day_of_week == 'daily' or activity.day_of_week == current_day:
            if activity.time:
                task_log = _get_or_create_task_log(patient.id, 'activity', activity.id, activity.time, today)
                tasks.append({
                    'task_log_id': task_log.id,
                    'type': 'activity',
                    'title': t('activity_reminder', lang),
                    'description': activity.name + (f' - {activity.description}' if activity.description else ''),
                    'time': activity.time,
                    'confirmed': task_log.confirmed,
                    'confirmed_at': task_log.confirmed_at.isoformat() if task_log.confirmed_at else None,
                    'icon': 'activity',
                })

    # Water reminders
    for wr in patient.water_reminders:
        water_times = generate_water_times(wr.start_time, wr.end_time, wr.interval_hours)
        for time_str in water_times:
            task_log = _get_or_create_task_log(patient.id, 'water', wr.id, time_str, today)
            tasks.append({
                'task_log_id': task_log.id,
                'type': 'water',
                'title': t('water_reminder', lang),
                'description': t('water_body', lang),
                'time': time_str,
                'confirmed': task_log.confirmed,
                'confirmed_at': task_log.confirmed_at.isoformat() if task_log.confirmed_at else None,
                'icon': 'water',
            })

    # Sort by time
    tasks.sort(key=lambda x: x['time'])
    return jsonify({'tasks': tasks, 'date': today.isoformat()})


@api_bp.route('/patient/tasks/<int:task_log_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_task(task_log_id):
    patient = _get_current_patient()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    task_log = TaskLog.query.filter_by(id=task_log_id, patient_id=patient.id).first()
    if not task_log:
        return jsonify({'error': 'Task not found'}), 404

    if task_log.confirmed:
        return jsonify({'message': 'Already confirmed'})

    task_log.confirmed = True
    task_log.confirmed_at = datetime.now(timezone.utc)

    # Notify caregiver
    lang = patient.language or 'ar'
    notification = Notification(
        patient_id=patient.id,
        caregiver_id=patient.caregiver_id,
        message=f"{patient.name}: {t('task_confirmed', lang)} - {task_log.task_type} ({task_log.scheduled_time})",
        type='confirmation',
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({'message': 'Task confirmed', 'confirmed_at': task_log.confirmed_at.isoformat()})


@api_bp.route('/patient/fcm-token', methods=['POST'])
@jwt_required()
def update_fcm_token():
    patient = _get_current_patient()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    data = request.get_json()
    patient.fcm_token = data.get('fcm_token', '')
    db.session.commit()
    return jsonify({'message': 'FCM token updated'})


@api_bp.route('/patient/caregiver-phone')
@jwt_required()
def caregiver_phone():
    patient = _get_current_patient()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
    return jsonify({'phone': patient.caregiver.phone or ''})


def _get_current_patient():
    patient_id = get_jwt_identity()
    return db.session.get(Patient, int(patient_id))


def _patient_profile(patient):
    """Serialize patient profile to dict."""
    return {
        'id': patient.id,
        'name': patient.name,
        'phone': patient.phone,
        'age': patient.age,
        'gender': patient.gender,
        'weight': patient.weight,
        'height': patient.height,
        'health_info': patient.health_info,
        'chronic_diseases': patient.chronic_diseases,
        'language': patient.language,
    }


def _get_or_create_task_log(patient_id, task_type, task_id, scheduled_time, today):
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
