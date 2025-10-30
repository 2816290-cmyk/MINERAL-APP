"""
Authentication helpers: user id + username generation, password hashing,
authentication, lockout, password reset tokens, and role decorator.
"""

import bcrypt
import secrets
import time
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import session, redirect, url_for, request, flash
from functools import wraps
from datetime import datetime

import config
from utils.data_loader import load_users, save_users, append_log

SECRET = config.SECRET_KEY
s = URLSafeTimedSerializer(SECRET)

# -------------------------
# Utilities (identity)
# -------------------------
def generate_user_id(first_name: str, last_name: str, country: str) -> str:
    """
    Generate a unique user id:
    Format: PREFIX + YYMMDD + first initials + random4 + checksum
    Example: MINN250715AB4829C
    We ensure uniqueness by checking existing users.
    """
    users = load_users().get("users", [])
    base_date = datetime.utcnow().strftime("%y%m%d")
    initials = (first_name[:1] + last_name[:1]).upper()
    attempt = 0
    while True:
        rand4 = secrets.randbelow(10000)
        core = f"{config.USER_ID_PREFIX}{base_date}{initials}{rand4:04d}"
        # simple checksum: mod 97
        checksum = sum(ord(c) for c in core) % 97
        user_id = f"{core}{checksum:02d}"
        if not any(u.get("user_id") == user_id for u in users):
            return user_id
        attempt += 1
        if attempt > 50:
            # fallback - add timestamp
            user_id = f"{core}{int(time.time())%10000}"
            if not any(u.get("user_id") == user_id for u in users):
                return user_id

def generate_username(first_name: str, last_name: str, country: str, org: str = "") -> str:
    """
    Create a readable username using available fields:
    format: firstname.lastname.countrycode[.orgshort][NNN]
    ensures uniqueness by appending numbers if needed.
    """
    users = load_users().get("users", [])
    fn = ''.join(ch for ch in first_name.lower() if ch.isalnum())
    ln = ''.join(ch for ch in last_name.lower() if ch.isalnum())
    cc = ''.join(ch for ch in country.lower() if ch.isalnum())[:3]
    orgshort = ''.join(ch for ch in org.lower() if ch.isalnum())[:3] if org else ""
    base = f"{fn}.{ln}.{cc}" + (f".{orgshort}" if orgshort else "")
    username = base
    suffix = 1
    existing = {u["username"] for u in users}
    while username in existing:
        username = f"{base}{suffix}"
        suffix += 1
    return username

# -------------------------
# Password helpers
# -------------------------
def hash_password(plain: str) -> str:
    """Return bcrypt hash (utf-8 string)"""
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

# -------------------------
# User management
# -------------------------
def create_user(first_name, last_name, email, country, org, role, password):
    # load user store
    data = load_users()
    users = data.setdefault("users", [])
    # generate identity values
    user_id = generate_user_id(first_name, last_name, country)
    username = generate_username(first_name, last_name, country, org)
    pw_hash = hash_password(password)
    created_at = datetime.utcnow().isoformat() + "Z"
    new_user = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "country": country,
        "organization": org,
        "role": role,
        "password_hash": pw_hash,
        "created_at": created_at,
        "failed_logins": 0,
        "locked_until": None
    }
    users.append(new_user)
    save_users(data)
    append_log({
        "timestamp": created_at,
        "event": "user_created",
        "user_id": user_id,
        "username": username,
        "role": role,
        "meta": {"email": email, "country": country}
    })
    return new_user

def find_user_by_username(username):
    users = load_users().get("users", [])
    for u in users:
        if u["username"] == username:
            return u
    return None

def find_user_by_email(email):
    users = load_users().get("users", [])
    for u in users:
        if u["email"].lower() == email.lower():
            return u
    return None

# -------------------------
# Authentication + lockout
# -------------------------
def authenticate(username, password, remote_ip=None):
    """Authenticate and handle failed attempts / lockout."""
    data = load_users()
    users = data.get("users", [])
    user = find_user_by_username(username)
    now = datetime.utcnow().isoformat() + "Z"
    if user is None:
        append_log({"timestamp": now, "event": "login_failed", "username": username, "reason": "no_user", "ip": remote_ip})
        return False, "Invalid credentials."

    # check lockout
    locked_until = user.get("locked_until")
    if locked_until:
        try:
            # stored as isoformat
            locked_ts = datetime.fromisoformat(locked_until.replace("Z", ""))
        except Exception:
            locked_ts = None
        if locked_ts and locked_ts > datetime.utcnow():
            append_log({"timestamp": now, "event": "login_blocked", "user_id": user["user_id"], "reason": "locked", "ip": remote_ip})
            return False, f"Account locked until {locked_until} UTC."

    if check_password(password, user["password_hash"]):
        # reset failed attempts
        user["failed_logins"] = 0
        user["locked_until"] = None
        save_users(data)
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["user_id"] = user["user_id"]
        append_log({"timestamp": now, "event": "login_success", "user_id": user["user_id"], "username": user["username"], "ip": remote_ip})
        return True, "Authenticated"
    else:
        # increment failed
        user["failed_logins"] = user.get("failed_logins", 0) + 1
        if user["failed_logins"] >= config.MAX_FAILED_LOGIN:
            # lock account
            lock_until = (datetime.utcnow().timestamp() + config.LOCKOUT_SECONDS)
            # store isoformat
            user["locked_until"] = datetime.utcfromtimestamp(lock_until).isoformat() + "Z"
            append_log({"timestamp": now, "event": "account_locked", "user_id": user["user_id"], "username": user["username"], "ip": remote_ip})
        else:
            append_log({"timestamp": now, "event": "login_failed", "user_id": user["user_id"], "username": user["username"], "attempts": user["failed_logins"], "ip": remote_ip})
        save_users(data)
        if user["failed_logins"] >= config.MAX_FAILED_LOGIN:
            return False, f"Too many failed attempts. Account locked until {user['locked_until']} UTC."
        return False, "Invalid credentials."

# -------------------------
# Token for password reset
# -------------------------
def generate_reset_token(email: str) -> str:
    """Return a token that expires after PASSWORD_RESET_EXP_SECONDS."""
    return s.dumps(email, salt=config.PASSWORD_RESET_SALT)

def verify_reset_token(token: str, max_age: int = None) -> str:
    if max_age is None:
        max_age = config.PASSWORD_RESET_EXP_SECONDS
    try:
        email = s.loads(token, salt=config.PASSWORD_RESET_SALT, max_age=max_age)
        return email
    except SignatureExpired:
        return None
    except BadSignature:
        return None

def reset_password(email: str, new_password: str):
    data = load_users()
    users = data.get("users", [])
    for u in users:
        if u["email"].lower() == email.lower():
            u["password_hash"] = hash_password(new_password)
            u["failed_logins"] = 0
            u["locked_until"] = None
            save_users(data)
            append_log({"timestamp": datetime.utcnow().isoformat()+"Z", "event": "password_reset", "user_id": u["user_id"], "username": u["username"]})
            return True
    return False

# -------------------------
# Role decorator
# -------------------------
def requires_role(roles):
    if isinstance(roles, str):
        allowed = [roles]
    else:
        allowed = list(roles)
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "username" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in allowed:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapped
    return decorator

# -------------------------
# Admin-only helper
# -------------------------
def unlock_account(user_id: str) -> bool:
    data = load_users()
    users = data.get("users", [])
    for u in users:
        if u["user_id"] == user_id:
            u["failed_logins"] = 0
            u["locked_until"] = None
            save_users(data)
            append_log({"timestamp": datetime.utcnow().isoformat()+"Z", "event": "account_unlocked", "user_id": user_id, "by": "admin"})
            return True
    return False
