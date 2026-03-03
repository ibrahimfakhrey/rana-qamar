import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'rana-secret-key-change-in-production')

    # Railway provides DATABASE_URL; fallback to local SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'rana.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'rana-jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 30 * 24 * 60 * 60  # 30 days in seconds

    FIREBASE_CREDENTIALS_PATH = os.environ.get(
        'FIREBASE_CREDENTIALS_PATH',
        os.path.join(BASE_DIR, 'firebase-credentials.json')
    )
    WTF_CSRF_ENABLED = True
