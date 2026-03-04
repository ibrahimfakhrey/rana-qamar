from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user, logout_user
from models import (db, Caregiver, Patient, Medication, Meal, Activity,
                    WaterReminder, Habit, Friend, TaskLog, Notification)

caregiver_bp = Blueprint('caregiver', __name__)


@caregiver_bp.route('/dashboard')
@login_required
def dashboard():
    patients = Patient.query.filter_by(caregiver_id=current_user.id).all()
    today = date.today()

    patient_stats = []
    for p in patients:
        total = TaskLog.query.filter_by(patient_id=p.id, date=today).count()
        confirmed = TaskLog.query.filter_by(patient_id=p.id, date=today, confirmed=True).count()
        patient_stats.append({
            'patient': p,
            'total_tasks': total,
            'confirmed_tasks': confirmed,
        })

    unread = Notification.query.filter_by(
        caregiver_id=current_user.id, read=False
    ).order_by(Notification.created_at.desc()).limit(20).all()

    return render_template('dashboard.html', patient_stats=patient_stats, notifications=unread)


@caregiver_bp.route('/patient/new', methods=['GET', 'POST'])
@login_required
def patient_new():
    if request.method == 'POST':
        return _save_patient(None)
    return render_template('patient_form.html', patient=None)


@caregiver_bp.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.caregiver_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('caregiver.dashboard'))

    today = date.today()
    tasks = TaskLog.query.filter_by(patient_id=patient.id, date=today)\
        .order_by(TaskLog.scheduled_time).all()

    notifications = Notification.query.filter_by(patient_id=patient.id)\
        .order_by(Notification.created_at.desc()).limit(20).all()

    return render_template('patient_detail.html', patient=patient, tasks=tasks, notifications=notifications)


@caregiver_bp.route('/patient/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
def patient_edit(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.caregiver_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('caregiver.dashboard'))

    if request.method == 'POST':
        return _save_patient(patient)
    return render_template('patient_form.html', patient=patient)


@caregiver_bp.route('/patient/<int:patient_id>/delete', methods=['POST'])
@login_required
def patient_delete(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.caregiver_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('caregiver.dashboard'))

    db.session.delete(patient)
    db.session.commit()
    flash('Patient deleted.', 'success')
    return redirect(url_for('caregiver.dashboard'))


@caregiver_bp.route('/delete-account', methods=['GET', 'POST'])
@login_required
def delete_account():
    caregiver = db.session.get(Caregiver, current_user.id)

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

    Notification.query.filter_by(caregiver_id=caregiver.id).delete()
    logout_user()
    db.session.delete(caregiver)
    db.session.commit()

    flash('Your account has been deleted.', 'success')
    return redirect(url_for('auth.login'))


@caregiver_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    Notification.query.filter_by(caregiver_id=current_user.id, read=False)\
        .update({'read': True})
    db.session.commit()
    return redirect(request.referrer or url_for('caregiver.dashboard'))


@caregiver_bp.route('/api/notifications/unread')
@login_required
def unread_notifications():
    """AJAX endpoint for notification polling."""
    notifications = Notification.query.filter_by(
        caregiver_id=current_user.id, read=False
    ).order_by(Notification.created_at.desc()).limit(20).all()

    return {
        'count': len(notifications),
        'notifications': [{
            'id': n.id,
            'message': n.message,
            'type': n.type,
            'created_at': n.created_at.isoformat() if n.created_at else '',
        } for n in notifications]
    }


def _save_patient(patient):
    """Create or update a patient with all related data."""
    is_new = patient is None

    if is_new:
        patient = Patient(caregiver_id=current_user.id)

    # Basic info
    patient.name = request.form.get('name', '').strip()
    patient.phone = request.form.get('phone', '').strip()
    patient.age = _int_or_none(request.form.get('age'))
    patient.gender = request.form.get('gender', '')
    patient.weight = _float_or_none(request.form.get('weight'))
    patient.height = _float_or_none(request.form.get('height'))
    patient.health_info = request.form.get('health_info', '').strip()
    patient.chronic_diseases = request.form.get('chronic_diseases', '').strip()
    patient.language = request.form.get('language', 'ar')

    # Login credentials
    patient.login_username = request.form.get('login_username', '').strip()
    password = request.form.get('login_password', '').strip()
    if password:
        patient.set_password(password)
    elif is_new:
        flash('Password is required for new patients.', 'danger')
        return render_template('patient_form.html', patient=patient)

    if is_new:
        db.session.add(patient)
    db.session.flush()

    # --- Medications ---
    Medication.query.filter_by(patient_id=patient.id).delete()
    med_names = request.form.getlist('med_name[]')
    med_dosages = request.form.getlist('med_dosage[]')
    med_times_list = request.form.getlist('med_times[]')
    for i, name in enumerate(med_names):
        if not name.strip():
            continue
        times_str = med_times_list[i] if i < len(med_times_list) else ''
        specific_times = [t.strip() for t in times_str.split(',') if t.strip()]
        db.session.add(Medication(
            patient_id=patient.id,
            name=name.strip(),
            dosage=med_dosages[i].strip() if i < len(med_dosages) else '',
            times_per_day=len(specific_times),
            specific_times=specific_times,
        ))

    # --- Meals ---
    Meal.query.filter_by(patient_id=patient.id).delete()
    meal_types = request.form.getlist('meal_type[]')
    meal_descs = request.form.getlist('meal_description[]')
    meal_times = request.form.getlist('meal_time[]')
    for i, mtype in enumerate(meal_types):
        if not mtype.strip():
            continue
        db.session.add(Meal(
            patient_id=patient.id,
            meal_type=mtype.strip(),
            description=meal_descs[i].strip() if i < len(meal_descs) else '',
            time=meal_times[i].strip() if i < len(meal_times) else '',
        ))

    # --- Activities ---
    Activity.query.filter_by(patient_id=patient.id).delete()
    act_names = request.form.getlist('activity_name[]')
    act_descs = request.form.getlist('activity_description[]')
    act_days = request.form.getlist('activity_day[]')
    act_times = request.form.getlist('activity_time[]')
    for i, name in enumerate(act_names):
        if not name.strip():
            continue
        db.session.add(Activity(
            patient_id=patient.id,
            name=name.strip(),
            description=act_descs[i].strip() if i < len(act_descs) else '',
            day_of_week=act_days[i].strip() if i < len(act_days) else 'daily',
            time=act_times[i].strip() if i < len(act_times) else '',
        ))

    # --- Water Reminder ---
    WaterReminder.query.filter_by(patient_id=patient.id).delete()
    water_interval = _float_or_none(request.form.get('water_interval'))
    if water_interval:
        db.session.add(WaterReminder(
            patient_id=patient.id,
            interval_hours=water_interval,
            start_time=request.form.get('water_start', '07:00'),
            end_time=request.form.get('water_end', '21:00'),
        ))

    # --- Habits ---
    Habit.query.filter_by(patient_id=patient.id).delete()
    habit_names = request.form.getlist('habit_name[]')
    habit_descs = request.form.getlist('habit_description[]')
    for i, name in enumerate(habit_names):
        if not name.strip():
            continue
        db.session.add(Habit(
            patient_id=patient.id,
            name=name.strip(),
            description=habit_descs[i].strip() if i < len(habit_descs) else '',
        ))

    # --- Friends ---
    Friend.query.filter_by(patient_id=patient.id).delete()
    friend_names = request.form.getlist('friend_name[]')
    friend_phones = request.form.getlist('friend_phone[]')
    friend_rels = request.form.getlist('friend_relationship[]')
    for i, name in enumerate(friend_names):
        if not name.strip():
            continue
        db.session.add(Friend(
            patient_id=patient.id,
            name=name.strip(),
            phone=friend_phones[i].strip() if i < len(friend_phones) else '',
            relationship=friend_rels[i].strip() if i < len(friend_rels) else '',
        ))

    db.session.commit()
    flash('Patient saved successfully!', 'success')
    return redirect(url_for('caregiver.patient_detail', patient_id=patient.id))


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def _float_or_none(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None
