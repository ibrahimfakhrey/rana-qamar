import os
import json
import logging

logger = logging.getLogger(__name__)

_firebase_initialized = False


def init_firebase(credentials_path):
    """Initialize Firebase Admin SDK from file or FIREBASE_CREDENTIALS env var."""
    global _firebase_initialized
    if _firebase_initialized:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Try env var first (for Railway), then file
        creds_json = os.environ.get('FIREBASE_CREDENTIALS')
        if creds_json:
            cred_dict = json.loads(creds_json)
            cred = credentials.Certificate(cred_dict)
        elif os.path.exists(credentials_path):
            cred = credentials.Certificate(credentials_path)
        else:
            logger.warning("Firebase credentials not found. Push notifications disabled.")
            return False

        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return False


def send_push_notification(fcm_token, title, body, data=None):
    """Send a push notification via Firebase Cloud Messaging."""
    if not _firebase_initialized or not fcm_token:
        return False

    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
        )
        messaging.send(message)
        logger.info(f"Push notification sent: {title}")
        return True
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False
