from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Caregiver(UserMixin, db.Model):
    __tablename__ = 'caregivers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    patients = db.relationship('Patient', backref='caregiver', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Patient(db.Model):
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    caregiver_id = db.Column(db.Integer, db.ForeignKey('caregivers.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    health_info = db.Column(db.Text)
    chronic_diseases = db.Column(db.Text)
    language = db.Column(db.String(5), default='ar')
    login_username = db.Column(db.String(80), unique=True, nullable=False)
    login_password_hash = db.Column(db.String(256), nullable=False)
    fcm_token = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    medications = db.relationship('Medication', backref='patient', lazy=True, cascade='all, delete-orphan')
    meals = db.relationship('Meal', backref='patient', lazy=True, cascade='all, delete-orphan')
    activities = db.relationship('Activity', backref='patient', lazy=True, cascade='all, delete-orphan')
    water_reminders = db.relationship('WaterReminder', backref='patient', lazy=True, cascade='all, delete-orphan')
    habits = db.relationship('Habit', backref='patient', lazy=True, cascade='all, delete-orphan')
    friends = db.relationship('Friend', backref='patient', lazy=True, cascade='all, delete-orphan')
    task_logs = db.relationship('TaskLog', backref='patient', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='patient', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.login_password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.login_password_hash, password)


class Medication(db.Model):
    __tablename__ = 'medications'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50))
    times_per_day = db.Column(db.Integer, default=1)
    specific_times = db.Column(db.JSON, default=list)  # ["08:00", "14:00"]


class Meal(db.Model):
    __tablename__ = 'meals'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    meal_type = db.Column(db.String(50), nullable=False)  # breakfast, lunch, dinner, snack
    description = db.Column(db.Text)
    time = db.Column(db.String(5))  # "HH:MM"


class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    day_of_week = db.Column(db.String(20))  # monday, tuesday, etc. or 'daily'
    time = db.Column(db.String(5))  # "HH:MM"


class WaterReminder(db.Model):
    __tablename__ = 'water_reminders'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    interval_hours = db.Column(db.Float, default=2.0)
    start_time = db.Column(db.String(5), default='07:00')  # "HH:MM"
    end_time = db.Column(db.String(5), default='21:00')  # "HH:MM"


class Habit(db.Model):
    __tablename__ = 'habits'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)


class Friend(db.Model):
    __tablename__ = 'friends'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    relationship = db.Column(db.String(50))


class TaskLog(db.Model):
    __tablename__ = 'task_logs'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    task_type = db.Column(db.String(20), nullable=False)  # medication, meal, water, activity
    task_id = db.Column(db.Integer)  # FK to the specific task table
    scheduled_time = db.Column(db.String(5))  # "HH:MM"
    date = db.Column(db.Date, nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    confirmed_at = db.Column(db.DateTime)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    caregiver_id = db.Column(db.Integer, db.ForeignKey('caregivers.id'))
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20))  # confirmation, reminder, alert
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
