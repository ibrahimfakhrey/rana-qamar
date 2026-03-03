import os
from datetime import timedelta

from flask import Flask
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import db, Caregiver
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
    from routes.caregiver_api import caregiver_api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(caregiver_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(caregiver_api_bp)

    # Exempt API from CSRF
    csrf.exempt(api_bp)
    csrf.exempt(caregiver_api_bp)

    # Create tables
    with app.app_context():
        db.create_all()

    # Init Firebase
    init_firebase(app.config['FIREBASE_CREDENTIALS_PATH'])

    # Start scheduler (avoid duplicate in debug reloader)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_scheduler(app)

    return app


# Gunicorn entry point
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
