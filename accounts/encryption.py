from cryptography.fernet import Fernet
from django.conf import settings
import os


def get_encryption_key():
    # Production: use a stable key from the environment (required on serverless
    # platforms like Vercel where the filesystem is read-only).
    env_key = os.environ.get('ENCRYPTION_KEY')
    if env_key:
        return env_key.encode()
    # Local development: store the key in a file that is gitignored.
    key_path = os.path.join(settings.BASE_DIR, '.encryption_key')
    if os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_path, 'wb') as f:
            f.write(key)
        return key


_fernet = None

def get_fernet():
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_encryption_key())
    return _fernet

def encrypt_data(data):
    if data is None:
        return None
    f = get_fernet()
    return f.encrypt(data.encode()).decode()

def decrypt_data(data):
    if data is None:
        return None
    f = get_fernet()
    try:
        return f.decrypt(data.encode()).decode()
    except Exception:
        return '[decryption error]'
