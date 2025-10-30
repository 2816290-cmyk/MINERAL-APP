import os
from datetime import timedelta

# Basic config - change SECRET_KEY to an env var in production
SECRET_KEY = os.environ.get("SECRET_KEY", "replace_this_with_a_secret_in_prod")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")

# Security settings
PASSWORD_RESET_SALT = "password-reset-salt"
PASSWORD_RESET_EXP_SECONDS = 3600  # 1 hour
MAX_FAILED_LOGIN = 5
LOCKOUT_SECONDS = 15 * 60  # 15 minutes

# Identity generation settings
USER_ID_PREFIX = "MINN"  # application code prefix for user id

# Flask session lifetime
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
