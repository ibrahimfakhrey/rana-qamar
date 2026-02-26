from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from models import db, Caregiver

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        caregiver = Caregiver.query.filter_by(email=email).first()
        if caregiver and caregiver.check_password(password):
            login_user(caregiver)
            return redirect(url_for('caregiver.dashboard'))
        flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if Caregiver.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        caregiver = Caregiver(name=name, email=email, phone=phone)
        caregiver.set_password(password)
        db.session.add(caregiver)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
