from datetime import datetime, date, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)
from models import (
    db, Caregiver, Patient, Medication, Meal, Activity,
    WaterReminder, Habit, Friend, TaskLog, Notification
)
from scheduler import generate_water_times
from translations import t, get_meal_type_name

caregiver_api_bp = Blueprint('caregiver_api', __name__, url_prefix='/api/caregiver')


def _get_current_caregiver():
    claims = get_jwt()
    role = claims.get('role', '')
    if role != 'caregiver':
        return None
    caregiver_id = get_jwt_identity()
    return db.session.get(Caregiver, int(caregiver_id))


# ── Auth ──────────────────────────────────────────────

@caregiver_api_bp.route('/register', methods=['POST'])
def caregiver_register():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({'error': 'Name, email and password are required'}), 400

    if Caregiver.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    caregiver = Caregiver(name=name, email=email, phone=phone)
    caregiver.set_password(password)
    db.session.add(caregiver)
    db.session.commit()

    token = create_access_token(
        identity=str(caregiver.id),
        additional_claims={'role': 'caregiver'}
    )
    return jsonify({
        'token': token,
        'caregiver': _caregiver_profile(caregiver),
    }), 201


@caregiver_api_bp.route('/login', methods=['POST'])
def caregiver_login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    caregiver = Caregiver.query.filter_by(email=email).first()
    if not caregiver or not caregiver.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = create_access_token(
        identity=str(caregiver.id),
        additional_claims={'role': 'caregiver'}
    )
    return jsonify({
        'token': token,
        'caregiver': _caregiver_profile(caregiver),
    })


# ── Profile ───────────────────────────────────────────

@caregiver_api_bp.route('/profile')
@jwt_required()
def caregiver_profile():
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify(_caregiver_profile(caregiver))


# ── Delete Account ────────────────────────────────────

@caregiver_api_bp.route('/delete-account', methods=['DELETE'])
@jwt_required()
def delete_account():
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403

    # Delete all patients and their nested data
    for patient in caregiver.patients:
        TaskLog.query.filter_by(patient_id=patient.id).delete()
        Notification.query.filter_by(patient_id=patient.id).delete()
        Medication.query.filter_by(patient_id=patient.id).delete()
        Meal.query.filter_by(patient_id=patient.id).delete()
        Activity.query.filter_by(patient_id=patient.id).delete()
        WaterReminder.query.filter_by(patient_id=patient.id).delete()
        Habit.query.filter_by(patient_id=patient.id).delete()
        Friend.query.filter_by(patient_id=patient.id).delete()
        db.session.delete(patient)

    # Delete remaining notifications for this caregiver
    Notification.query.filter_by(caregiver_id=caregiver.id).delete()

    db.session.delete(caregiver)
    db.session.commit()

    return jsonify({'message': 'Account deleted successfully'})


# ── Patient CRUD ──────────────────────────────────────

@caregiver_api_bp.route('/patients')
@jwt_required()
def list_patients():
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403

    today = date.today()
    patients = []
    for p in caregiver.patients:
        total = TaskLog.query.filter_by(patient_id=p.id, date=today).count()
        confirmed = TaskLog.query.filter_by(patient_id=p.id, date=today, confirmed=True).count()
        patients.append({
            'id': p.id,
            'name': p.name,
            'age': p.age,
            'gender': p.gender,
            'phone': p.phone,
            'language': p.language,
            'total_tasks': total,
            'confirmed_tasks': confirmed,
        })
    return jsonify({'patients': patients})


@caregiver_api_bp.route('/patients', methods=['POST'])
@jwt_required()
def create_patient():
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()

    # Validate required fields
    name = data.get('name', '').strip()
    username = data.get('login_username', '').strip()
    password = data.get('login_password', '')
    if not name or not username or not password:
        return jsonify({'error': 'Name, username and password are required'}), 400

    if Patient.query.filter_by(login_username=username).first():
        return jsonify({'error': 'Username already taken'}), 409

    patient = Patient(
        caregiver_id=caregiver.id,
        name=name,
        phone=data.get('phone', ''),
        age=data.get('age'),
        gender=data.get('gender', ''),
        weight=data.get('weight'),
        height=data.get('height'),
        health_info=data.get('health_info', ''),
        chronic_diseases=data.get('chronic_diseases', ''),
        language=data.get('language', 'ar'),
        login_username=username,
    )
    patient.set_password(password)
    db.session.add(patient)
    db.session.flush()  # get patient.id

    # Nested data
    _save_nested_data(patient, data)
    db.session.commit()

    return jsonify({'patient': _full_patient(patient)}), 201


@caregiver_api_bp.route('/patients/<int:patient_id>')
@jwt_required()
def get_patient(patient_id):
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403

    patient = Patient.query.filter_by(id=patient_id, caregiver_id=caregiver.id).first()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    return jsonify({'patient': _full_patient(patient)})


@caregiver_api_bp.route('/patients/<int:patient_id>', methods=['PUT'])
@jwt_required()
def update_patient(patient_id):
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403

    patient = Patient.query.filter_by(id=patient_id, caregiver_id=caregiver.id).first()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    data = request.get_json()

    # Update basic fields
    if 'name' in data:
        patient.name = data['name']
    if 'phone' in data:
        patient.phone = data['phone']
    if 'age' in data:
        patient.age = data['age']
    if 'gender' in data:
        patient.gender = data['gender']
    if 'weight' in data:
        patient.weight = data['weight']
    if 'height' in data:
        patient.height = data['height']
    if 'health_info' in data:
        patient.health_info = data['health_info']
    if 'chronic_diseases' in data:
        patient.chronic_diseases = data['chronic_diseases']
    if 'language' in data:
        patient.language = data['language']

    # Update password if provided
    if data.get('login_password'):
        patient.set_password(data['login_password'])

    # Update username if provided
    if 'login_username' in data and data['login_username'] != patient.login_username:
        if Patient.query.filter_by(login_username=data['login_username']).first():
            return jsonify({'error': 'Username already taken'}), 409
        patient.login_username = data['login_username']

    # Replace nested data
    _clear_nested_data(patient)
    _save_nested_data(patient, data)
    db.session.commit()

    return jsonify({'patient': _full_patient(patient)})


@caregiver_api_bp.route('/patients/<int:patient_id>', methods=['DELETE'])
@jwt_required()
def delete_patient(patient_id):
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403

    patient = Patient.query.filter_by(id=patient_id, caregiver_id=caregiver.id).first()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    db.session.delete(patient)
    db.session.commit()
    return jsonify({'message': 'Patient deleted'})


# ── Patient Tasks ─────────────────────────────────────

@caregiver_api_bp.route('/patients/<int:patient_id>/tasks/today')
@jwt_required()
def patient_tasks_today(patient_id):
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403

    patient = Patient.query.filter_by(id=patient_id, caregiver_id=caregiver.id).first()
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    today = date.today()
    current_day = datetime.now().strftime('%A').lower()
    lang = patient.language or 'ar'
    tasks = []

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

    tasks.sort(key=lambda x: x['time'])
    return jsonify({'tasks': tasks, 'date': today.isoformat()})


# ── Notifications ─────────────────────────────────────

@caregiver_api_bp.route('/notifications')
@jwt_required()
def caregiver_notifications():
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403

    notifications = Notification.query.filter_by(
        caregiver_id=caregiver.id
    ).order_by(Notification.created_at.desc()).limit(100).all()

    return jsonify({
        'notifications': [
            {
                'id': n.id,
                'patient_id': n.patient_id,
                'patient_name': n.patient.name if n.patient else '',
                'message': n.message,
                'type': n.type,
                'read': n.read,
                'created_at': n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
        'unread_count': sum(1 for n in notifications if not n.read),
    })


@caregiver_api_bp.route('/notifications/mark-read', methods=['POST'])
@jwt_required()
def mark_notifications_read():
    caregiver = _get_current_caregiver()
    if not caregiver:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    ids = data.get('ids')

    query = Notification.query.filter_by(caregiver_id=caregiver.id, read=False)
    if ids:
        query = query.filter(Notification.id.in_(ids))
    query.update({Notification.read: True}, synchronize_session=False)
    db.session.commit()

    return jsonify({'message': 'Notifications marked as read'})


# ── Helpers ───────────────────────────────────────────

def _caregiver_profile(caregiver):
    return {
        'id': caregiver.id,
        'name': caregiver.name,
        'email': caregiver.email,
        'phone': caregiver.phone,
        'created_at': caregiver.created_at.isoformat() if caregiver.created_at else None,
    }


def _full_patient(patient):
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
        'login_username': patient.login_username,
        'medications': [
            {
                'id': m.id,
                'name': m.name,
                'dosage': m.dosage,
                'times_per_day': m.times_per_day,
                'specific_times': m.specific_times or [],
            }
            for m in patient.medications
        ],
        'meals': [
            {
                'id': m.id,
                'meal_type': m.meal_type,
                'description': m.description,
                'time': m.time,
            }
            for m in patient.meals
        ],
        'activities': [
            {
                'id': a.id,
                'name': a.name,
                'description': a.description,
                'day_of_week': a.day_of_week,
                'time': a.time,
            }
            for a in patient.activities
        ],
        'water_reminders': [
            {
                'id': w.id,
                'interval_hours': w.interval_hours,
                'start_time': w.start_time,
                'end_time': w.end_time,
            }
            for w in patient.water_reminders
        ],
        'habits': [
            {
                'id': h.id,
                'name': h.name,
                'description': h.description,
            }
            for h in patient.habits
        ],
        'friends': [
            {
                'id': f.id,
                'name': f.name,
                'phone': f.phone,
                'relationship': f.relationship,
            }
            for f in patient.friends
        ],
    }


def _save_nested_data(patient, data):
    for med in data.get('medications', []):
        db.session.add(Medication(
            patient_id=patient.id,
            name=med.get('name', ''),
            dosage=med.get('dosage', ''),
            times_per_day=med.get('times_per_day', 1),
            specific_times=med.get('specific_times', []),
        ))

    for meal in data.get('meals', []):
        db.session.add(Meal(
            patient_id=patient.id,
            meal_type=meal.get('meal_type', ''),
            description=meal.get('description', ''),
            time=meal.get('time', ''),
        ))

    for act in data.get('activities', []):
        db.session.add(Activity(
            patient_id=patient.id,
            name=act.get('name', ''),
            description=act.get('description', ''),
            day_of_week=act.get('day_of_week', 'daily'),
            time=act.get('time', ''),
        ))

    for wr in data.get('water_reminders', []):
        db.session.add(WaterReminder(
            patient_id=patient.id,
            interval_hours=wr.get('interval_hours', 2.0),
            start_time=wr.get('start_time', '07:00'),
            end_time=wr.get('end_time', '21:00'),
        ))

    for habit in data.get('habits', []):
        db.session.add(Habit(
            patient_id=patient.id,
            name=habit.get('name', ''),
            description=habit.get('description', ''),
        ))

    for friend in data.get('friends', []):
        db.session.add(Friend(
            patient_id=patient.id,
            name=friend.get('name', ''),
            phone=friend.get('phone', ''),
            relationship=friend.get('relationship', ''),
        ))


def _clear_nested_data(patient):
    Medication.query.filter_by(patient_id=patient.id).delete()
    Meal.query.filter_by(patient_id=patient.id).delete()
    Activity.query.filter_by(patient_id=patient.id).delete()
    WaterReminder.query.filter_by(patient_id=patient.id).delete()
    Habit.query.filter_by(patient_id=patient.id).delete()
    Friend.query.filter_by(patient_id=patient.id).delete()


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
