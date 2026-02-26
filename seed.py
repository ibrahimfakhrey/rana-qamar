"""Seed script to populate the database with sample data."""
from app import create_app
from models import db, Caregiver, Patient, Medication, Meal, Activity, WaterReminder, Habit, Friend

app = create_app()

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()

    # Create caregiver
    caregiver = Caregiver(name='سارة أحمد', email='sara@example.com', phone='0501234567')
    caregiver.set_password('password123')
    db.session.add(caregiver)
    db.session.flush()

    # Create patient
    patient = Patient(
        caregiver_id=caregiver.id,
        name='محمد أحمد',
        phone='0507654321',
        age=72,
        gender='male',
        weight=75.0,
        height=170.0,
        health_info='مريض ألزهايمر - مرحلة مبكرة',
        chronic_diseases='ضغط الدم، السكري',
        language='ar',
        login_username='mohammed',
    )
    patient.set_password('1234')
    db.session.add(patient)
    db.session.flush()

    # Medications
    db.session.add_all([
        Medication(patient_id=patient.id, name='أملوديبين', dosage='5mg', times_per_day=1, specific_times=['08:00']),
        Medication(patient_id=patient.id, name='ميتفورمين', dosage='500mg', times_per_day=2, specific_times=['08:00', '20:00']),
        Medication(patient_id=patient.id, name='دونيبيزيل', dosage='10mg', times_per_day=1, specific_times=['21:00']),
    ])

    # Meals
    db.session.add_all([
        Meal(patient_id=patient.id, meal_type='breakfast', description='خبز وجبن وبيض مسلوق', time='07:30'),
        Meal(patient_id=patient.id, meal_type='lunch', description='أرز ودجاج مشوي وسلطة', time='12:30'),
        Meal(patient_id=patient.id, meal_type='dinner', description='شوربة خضار وخبز', time='18:30'),
        Meal(patient_id=patient.id, meal_type='snack', description='فواكه طازجة', time='15:00'),
    ])

    # Activities
    db.session.add_all([
        Activity(patient_id=patient.id, name='المشي الصباحي', description='مشي خفيف لمدة 20 دقيقة', day_of_week='daily', time='06:30'),
        Activity(patient_id=patient.id, name='تمارين الذاكرة', description='حل ألغاز وتمارين ذهنية', day_of_week='daily', time='10:00'),
        Activity(patient_id=patient.id, name='قراءة القرآن', description='قراءة جزء من القرآن', day_of_week='daily', time='16:00'),
    ])

    # Water reminder
    db.session.add(WaterReminder(patient_id=patient.id, interval_hours=2, start_time='07:00', end_time='21:00'))

    # Habits
    db.session.add_all([
        Habit(patient_id=patient.id, name='يحب القهوة العربية', description='كوب واحد صباحاً'),
        Habit(patient_id=patient.id, name='يستمتع بالحدائق', description='يحب الجلوس في الحديقة بعد العصر'),
    ])

    # Friends
    db.session.add_all([
        Friend(patient_id=patient.id, name='عبدالله خالد', phone='0509876543', relationship='صديق'),
        Friend(patient_id=patient.id, name='فاطمة محمد', phone='0501111111', relationship='جارة'),
    ])

    db.session.commit()
    print("Database seeded successfully!")
    print(f"Caregiver login: sara@example.com / password123")
    print(f"Patient login: mohammed / 1234")
