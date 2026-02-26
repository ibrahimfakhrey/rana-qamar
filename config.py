import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_database_uri():
    """Get database URI, handling Railway's variable names and postgres:// prefix."""
    uri = (os.environ.get('DATABASE_URL')
           or os.environ.get('DATABASE_PRIVATE_URL')
           or os.environ.get('DATABASE_PUBLIC_URL')
           or f"sqlite:///{os.path.join(BASE_DIR, 'rana.db')}")
    # SQLAlchemy requires postgresql:// not postgres://
    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)
    return uri


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'rana-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'rana-jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 30 * 24 * 60 * 60  # 30 days in seconds
    FIREBASE_CREDENTIALS_PATH = os.environ.get(
        'FIREBASE_CREDENTIALS_PATH',
        os.path.join(BASE_DIR, 'firebase-credentials.json')
    )
    WTF_CSRF_ENABLED = True
