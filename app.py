import os
from datetime import timedelta

from flask import Flask
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import (db, Caregiver, Patient, Medication, Meal, Activity,
                    WaterReminder, Habit, Friend)
from notifications import init_firebase
from scheduler import start_scheduler

login_manager = LoginManager()
jwt = JWTManager()
migrate = Migrate()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Caregiver, int(user_id))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.caregiver import caregiver_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(caregiver_bp)
    app.register_blueprint(api_bp)

    # Exempt API from CSRF
    csrf.exempt(api_bp)

    # Create tables and seed on first run
    with app.app_context():
        db.create_all()
        _seed_if_empty()

    # Init Firebase
    init_firebase(app.config['FIREBASE_CREDENTIALS_PATH'])

    # Start scheduler (avoid duplicate in debug reloader)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_scheduler(app)

    return app


def _seed_if_empty():
    """Seed database with sample data only if no caregivers exist."""
    if Caregiver.query.first() is not None:
        return

    caregiver = Caregiver(name='سارة أحمد', email='sara@example.com', phone='0501234567')
    caregiver.set_password('password123')
    db.session.add(caregiver)
    db.session.flush()

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

    db.session.add_all([
        Medication(patient_id=patient.id, name='أملوديبين', dosage='5mg', times_per_day=1, specific_times=['08:00']),
        Medication(patient_id=patient.id, name='ميتفورمين', dosage='500mg', times_per_day=2, specific_times=['08:00', '20:00']),
        Medication(patient_id=patient.id, name='دونيبيزيل', dosage='10mg', times_per_day=1, specific_times=['21:00']),
    ])
    db.session.add_all([
        Meal(patient_id=patient.id, meal_type='breakfast', description='خبز وجبن وبيض مسلوق', time='07:30'),
        Meal(patient_id=patient.id, meal_type='lunch', description='أرز ودجاج مشوي وسلطة', time='12:30'),
        Meal(patient_id=patient.id, meal_type='dinner', description='شوربة خضار وخبز', time='18:30'),
        Meal(patient_id=patient.id, meal_type='snack', description='فواكه طازجة', time='15:00'),
    ])
    db.session.add_all([
        Activity(patient_id=patient.id, name='المشي الصباحي', description='مشي خفيف لمدة 20 دقيقة', day_of_week='daily', time='06:30'),
        Activity(patient_id=patient.id, name='تمارين الذاكرة', description='حل ألغاز وتمارين ذهنية', day_of_week='daily', time='10:00'),
        Activity(patient_id=patient.id, name='قراءة القرآن', description='قراءة جزء من القرآن', day_of_week='daily', time='16:00'),
    ])
    db.session.add(WaterReminder(patient_id=patient.id, interval_hours=2, start_time='07:00', end_time='21:00'))
    db.session.add_all([
        Habit(patient_id=patient.id, name='يحب القهوة العربية', description='كوب واحد صباحاً'),
        Habit(patient_id=patient.id, name='يستمتع بالحدائق', description='يحب الجلوس في الحديقة بعد العصر'),
    ])
    db.session.add_all([
        Friend(patient_id=patient.id, name='عبدالله خالد', phone='0509876543', relationship='صديق'),
        Friend(patient_id=patient.id, name='فاطمة محمد', phone='0501111111', relationship='جارة'),
    ])
    db.session.commit()
    print("Database seeded with sample data!")


# Gunicorn entry point
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
