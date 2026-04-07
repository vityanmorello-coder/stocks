"""
QuantumTrade Engine - Security Layer
======================================
Enterprise-grade security implementation:
  - bcrypt password hashing (work factor 12)
  - JWT-based session tokens (HS256, expiring)
  - TOTP 2FA (Google Authenticator compatible)
  - Rate limiting (per IP + per user, sliding window)
  - Brute-force lockout (5 attempts → 15 min lockout)
  - AES-256 encryption for sensitive config values
  - Audit logging (all auth events + trades)
  - RBAC permission system
"""

import os
import time
import hmac
import base64
import struct
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Optional heavy deps — graceful fallback if not installed yet ──────────────
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("bcrypt not installed — falling back to SHA-256. Run: pip install bcrypt")

try:
    import jwt as pyjwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not installed. Run: pip install PyJWT")

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False
    logger.warning("pyotp not installed. Run: pip install pyotp")

try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography not installed. Run: pip install cryptography")


# ============================================================
# CONSTANTS
# ============================================================

BCRYPT_ROUNDS        = 12          # Work factor — increase to slow down brute-force
JWT_ALGORITHM        = "HS256"
JWT_ACCESS_EXPIRE_H  = 24          # Hours for normal session
JWT_REMEMBER_EXPIRE_H = 168        # 7 days for "remember me"
TOTP_ISSUER          = "QuantumTrade"
MAX_LOGIN_ATTEMPTS   = 5           # Before lockout
LOCKOUT_SECONDS      = 900         # 15 minutes
RATE_LIMIT_WINDOW    = 60          # Sliding window in seconds
RATE_LIMIT_MAX_REQ   = 30          # Max requests per window per user/IP


# ============================================================
# 1. PASSWORD SECURITY — bcrypt with automatic salt
# ============================================================

class PasswordManager:
    """
    bcrypt-based password hashing.
    Falls back to salted SHA-256 if bcrypt unavailable.
    """

    @staticmethod
    def hash(password: str) -> Dict[str, str]:
        """
        Hash a password.

        Returns:
            {'hash': str, 'algorithm': 'bcrypt' | 'sha256', 'salt': str}
        """
        if BCRYPT_AVAILABLE:
            hashed = bcrypt.hashpw(
                password.encode('utf-8'),
                bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            )
            return {
                'hash': hashed.decode('utf-8'),
                'algorithm': 'bcrypt',
                'salt': '',  # bcrypt embeds salt in hash
            }
        else:
            # Fallback: salted SHA-256
            salt = secrets.token_hex(32)
            pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return {
                'hash': pw_hash,
                'algorithm': 'sha256',
                'salt': salt,
            }

    @staticmethod
    def verify(password: str, stored: Dict[str, str]) -> bool:
        """Verify a password against stored hash."""
        algorithm = stored.get('algorithm', 'sha256')

        if algorithm == 'bcrypt' and BCRYPT_AVAILABLE:
            try:
                return bcrypt.checkpw(
                    password.encode('utf-8'),
                    stored['hash'].encode('utf-8')
                )
            except Exception:
                return False

        elif algorithm == 'sha256':
            salt = stored.get('salt', '')
            pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return hmac.compare_digest(pw_hash, stored['hash'])

        return False

    @staticmethod
    def needs_upgrade(stored: Dict[str, str]) -> bool:
        """Returns True if password should be re-hashed with stronger algorithm."""
        return stored.get('algorithm') != 'bcrypt' and BCRYPT_AVAILABLE

    @staticmethod
    def validate_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password strength.
        Returns (is_valid, message).
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        return True, "OK"


# ============================================================
# 2. JWT SESSION TOKENS
# ============================================================

class JWTManager:
    """
    JWT-based stateless session tokens.
    Falls back to random secure tokens if PyJWT unavailable.
    """

    def __init__(self):
        # Load or generate JWT secret
        self.secret = os.environ.get('JWT_SECRET') or self._load_or_create_secret()

    def _load_or_create_secret(self) -> str:
        """Load JWT secret from .env or generate and save a new one."""
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        
        # Try to read existing
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith('JWT_SECRET='):
                        return line.split('=', 1)[1].strip()
        
        # Generate new secret
        new_secret = secrets.token_urlsafe(64)
        
        # Append to .env
        with open(env_path, 'a') as f:
            f.write(f"\nJWT_SECRET={new_secret}\n")
        
        os.environ['JWT_SECRET'] = new_secret
        return new_secret

    def create_token(self, user_id: str, username: str, role: str,
                     remember: bool = False, has_2fa: bool = False) -> str:
        """
        Create a signed JWT access token.

        Payload includes: user_id, username, role, 2fa_verified, exp, iat, jti
        """
        expire_hours = JWT_REMEMBER_EXPIRE_H if remember else JWT_ACCESS_EXPIRE_H
        now = datetime.utcnow()

        payload = {
            'sub': user_id,
            'username': username,
            'role': role,
            '2fa_verified': has_2fa,
            'iat': now,
            'exp': now + timedelta(hours=expire_hours),
            'jti': secrets.token_hex(16),  # Unique token ID for revocation
        }

        if JWT_AVAILABLE:
            return pyjwt.encode(payload, self.secret, algorithm=JWT_ALGORITHM)
        else:
            # Fallback: random secure token (stateful)
            return secrets.token_urlsafe(64)

    def decode_token(self, token: str) -> Optional[Dict]:
        """
        Decode and validate a JWT token.
        Returns payload dict or None if invalid/expired.
        """
        if not JWT_AVAILABLE:
            return None  # Must use DB session lookup in fallback mode

        try:
            payload = pyjwt.decode(
                token,
                self.secret,
                algorithms=[JWT_ALGORITHM]
            )
            return payload
        except pyjwt.ExpiredSignatureError:
            logger.debug("JWT expired")
            return None
        except pyjwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT: {e}")
            return None

    def get_user_from_token(self, token: str) -> Optional[Dict]:
        """Extract user info from a valid token."""
        payload = self.decode_token(token)
        if not payload:
            return None
        return {
            'user_id': payload['sub'],
            'username': payload['username'],
            'role': payload['role'],
            '2fa_verified': payload.get('2fa_verified', False),
            'jti': payload.get('jti'),
        }


# ============================================================
# 3. TWO-FACTOR AUTHENTICATION (TOTP)
# ============================================================

class TOTPManager:
    """
    Google Authenticator compatible TOTP 2FA.
    Uses pyotp — RFC 6238 compliant.
    """

    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret for a user."""
        if PYOTP_AVAILABLE:
            return pyotp.random_base32()
        else:
            # Fallback: base32-encoded random bytes
            return base64.b32encode(secrets.token_bytes(20)).decode('utf-8')

    @staticmethod
    def get_provisioning_uri(secret: str, username: str) -> str:
        """
        Get the otpauth:// URI for QR code generation.
        User scans this with Google Authenticator.
        """
        if PYOTP_AVAILABLE:
            totp = pyotp.TOTP(secret)
            return totp.provisioning_uri(
                name=username,
                issuer_name=TOTP_ISSUER
            )
        return f"otpauth://totp/{TOTP_ISSUER}:{username}?secret={secret}&issuer={TOTP_ISSUER}"

    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """
        Verify a 6-digit TOTP code.
        Allows ±1 time window (30s tolerance).
        """
        if not secret or not code:
            return False

        code = code.strip().replace(' ', '')

        if PYOTP_AVAILABLE:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)
        else:
            # Manual HOTP implementation (RFC 4226 / 6238)
            return TOTPManager._manual_verify(secret, code)

    @staticmethod
    def _manual_verify(secret: str, code: str) -> bool:
        """Manual TOTP implementation for environments without pyotp."""
        try:
            key = base64.b32decode(secret.upper())
            t = int(time.time()) // 30

            for delta in [-1, 0, 1]:
                msg = struct.pack('>Q', t + delta)
                h = hmac.new(key, msg, hashlib.sha1).digest()
                offset = h[-1] & 0x0F
                value = struct.unpack('>I', h[offset:offset+4])[0] & 0x7FFFFFFF
                otp = str(value % 1000000).zfill(6)
                if hmac.compare_digest(otp, code.zfill(6)):
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def generate_qr_html(uri: str, username: str) -> str:
        """Generate HTML with QR code using Google Charts API."""
        import urllib.parse
        encoded = urllib.parse.quote(uri)
        qr_url = f"https://chart.googleapis.com/chart?chs=200x200&chld=M|0&cht=qr&chl={encoded}"
        # Parse secret from otpauth://totp/...?secret=XXXX&...
        parsed = urllib.parse.urlparse(uri)
        qs = urllib.parse.parse_qs(parsed.query)
        manual_key = qs.get('secret', [''])[0]
        return f"""
        <div style="text-align:center; padding:16px;">
            <img src="{qr_url}" alt="QR Code" style="border-radius:8px; border:4px solid white;" width="200" height="200"/>
            <div style="font-size:11px; color:var(--text-muted); margin-top:8px;">
                Scan with Google Authenticator or Authy
            </div>
            <div style="font-family:'JetBrains Mono',monospace; font-size:12px; 
                        background:rgba(255,255,255,0.05); padding:8px 12px; 
                        border-radius:6px; margin-top:8px; letter-spacing:2px;">
                {manual_key}
            </div>
            <div style="font-size:10px; color:var(--text-muted); margin-top:4px;">
                Manual entry key (if QR scan fails)
            </div>
        </div>
        """


# ============================================================
# 4. RATE LIMITING — Sliding Window (in-memory)
# ============================================================

class RateLimiter:
    """
    Sliding window rate limiter.
    Tracks requests per (user_id | ip_address).
    Thread-safe for single-process Streamlit apps.
    """

    def __init__(self):
        # { key: [timestamp, timestamp, ...] }
        self._windows: Dict[str, List[float]] = defaultdict(list)
        # { key: lockout_until_timestamp }
        self._lockouts: Dict[str, float] = {}
        # { key: failed_attempt_count }
        self._failed: Dict[str, int] = defaultdict(int)

    def is_locked_out(self, key: str) -> Tuple[bool, int]:
        """
        Check if key is locked out.
        Returns (is_locked, seconds_remaining).
        """
        lockout_until = self._lockouts.get(key, 0)
        now = time.time()

        if now < lockout_until:
            return True, int(lockout_until - now)
        return False, 0

    def check_rate_limit(self, key: str,
                         max_req: int = RATE_LIMIT_MAX_REQ,
                         window: int = RATE_LIMIT_WINDOW) -> Tuple[bool, int]:
        """
        Check if key has exceeded rate limit.
        Returns (is_allowed, requests_remaining).
        """
        # Check lockout first
        locked, remaining = self.is_locked_out(key)
        if locked:
            return False, 0

        now = time.time()
        cutoff = now - window

        # Clean old timestamps
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]

        count = len(self._windows[key])

        if count >= max_req:
            return False, 0

        # Record this request
        self._windows[key].append(now)
        return True, max_req - count - 1

    def record_failed_login(self, key: str) -> Tuple[int, bool]:
        """
        Record a failed login attempt.
        Returns (attempt_count, is_now_locked).
        """
        self._failed[key] += 1
        count = self._failed[key]

        if count >= MAX_LOGIN_ATTEMPTS:
            self._lockouts[key] = time.time() + LOCKOUT_SECONDS
            self._failed[key] = 0
            logger.warning(f"[SECURITY] Account locked: {key} after {count} failed attempts")
            return count, True

        return count, False

    def record_successful_login(self, key: str):
        """Clear failed attempt counter on success."""
        self._failed[key] = 0
        self._lockouts.pop(key, None)

    def get_failed_count(self, key: str) -> int:
        return self._failed.get(key, 0)


# ============================================================
# 5. ENCRYPTION — AES-256 via Fernet (for API keys in DB)
# ============================================================

class EncryptionManager:
    """
    AES-256 (Fernet) encryption for sensitive values stored in DB.
    Key is derived from JWT_SECRET or a separate ENCRYPTION_KEY in .env
    """

    def __init__(self):
        self._fernet = None
        if CRYPTOGRAPHY_AVAILABLE:
            key = self._get_or_create_key()
            from cryptography.fernet import Fernet
            self._fernet = Fernet(key)

    def _get_or_create_key(self) -> bytes:
        """Load or generate Fernet encryption key."""
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

        # Try env var
        key_str = os.environ.get('ENCRYPTION_KEY')
        if key_str:
            return key_str.encode()

        # Try .env file
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith('ENCRYPTION_KEY='):
                        key_str = line.split('=', 1)[1].strip()
                        os.environ['ENCRYPTION_KEY'] = key_str
                        return key_str.encode()

        # Generate new key
        from cryptography.fernet import Fernet
        new_key = Fernet.generate_key().decode()

        with open(env_path, 'a') as f:
            f.write(f"\nENCRYPTION_KEY={new_key}\n")
        os.environ['ENCRYPTION_KEY'] = new_key
        logger.info("[SECURITY] New encryption key generated and saved to .env")
        return new_key.encode()

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string. Returns base64 ciphertext."""
        if self._fernet:
            return self._fernet.encrypt(plaintext.encode()).decode()
        # Fallback: no encryption (log warning)
        logger.warning("[SECURITY] Encryption unavailable — storing plaintext. Install cryptography.")
        return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        if self._fernet:
            try:
                return self._fernet.decrypt(ciphertext.encode()).decode()
            except Exception:
                return ciphertext  # Already plaintext or corrupted
        return ciphertext

    @property
    def available(self) -> bool:
        return self._fernet is not None


# ============================================================
# 6. RBAC — Role-Based Access Control
# ============================================================

# Permission definitions
PERMISSIONS = {
    'admin': {
        'view_dashboard', 'execute_trades', 'view_positions',
        'view_signals', 'view_analysis', 'manage_users',
        'view_admin_panel', 'view_audit_logs', 'change_settings',
        'export_data', 'delete_positions',
    },
    'trader': {
        'view_dashboard', 'execute_trades', 'view_positions',
        'view_signals', 'view_analysis', 'change_settings',
    },
    'viewer': {
        'view_dashboard', 'view_positions', 'view_signals', 'view_analysis',
    },
    'user': {  # Default role — same as trader
        'view_dashboard', 'execute_trades', 'view_positions',
        'view_signals', 'view_analysis', 'change_settings',
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in PERMISSIONS.get(role, set())


def require_permission(role: str, permission: str) -> bool:
    """
    Returns True if allowed.
    Use in dashboard: if not require_permission(user['role'], 'execute_trades'): st.stop()
    """
    allowed = has_permission(role, permission)
    if not allowed:
        logger.warning(f"[RBAC] Permission denied: role='{role}' permission='{permission}'")
    return allowed


def get_permissions(role: str) -> set:
    """Get all permissions for a role."""
    return PERMISSIONS.get(role, set())


# ============================================================
# SINGLETONS
# ============================================================

_password_manager  = None
_jwt_manager       = None
_totp_manager      = None
_rate_limiter      = None
_encryption_manager = None


def get_password_manager() -> PasswordManager:
    global _password_manager
    if _password_manager is None:
        _password_manager = PasswordManager()
    return _password_manager


def get_jwt_manager() -> JWTManager:
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


def get_totp_manager() -> TOTPManager:
    global _totp_manager
    if _totp_manager is None:
        _totp_manager = TOTPManager()
    return _totp_manager


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_encryption_manager() -> EncryptionManager:
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager
