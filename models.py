"""
Database models for Wingman
SQLAlchemy models for users, audit logs, and OIDC providers
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()


class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)  # Nullable for SSO users

    # Role: admin, operator, viewer
    role = db.Column(db.String(20), nullable=False, default='viewer')

    # SSO/OIDC fields
    auth_provider = db.Column(db.String(50), default='local')  # 'local', 'oidc'
    external_id = db.Column(db.String(256), nullable=True, index=True)  # OIDC sub claim

    # Status and timestamps
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Security: Failed login tracking and account lockout
    failed_login_count = db.Column(db.Integer, default=0)
    failed_login_at = db.Column(db.DateTime, nullable=True)
    locked_until = db.Column(db.DateTime, nullable=True)

    # Security: Session invalidation (increment to force re-login)
    session_version = db.Column(db.Integer, default=0)

    # Security: Password change tracking
    password_changed_at = db.Column(db.DateTime, nullable=True)

    # Security: Force password change on first login
    must_change_password = db.Column(db.Boolean, default=False)

    # Profile fields from OIDC
    display_name = db.Column(db.String(200), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)

    def set_password(self, password: str):
        """Hash and set password, invalidate existing sessions"""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        self.password_changed_at = datetime.utcnow()
        # Increment session version to invalidate all existing sessions
        self.session_version = (self.session_version or 0) + 1

    def check_password(self, password: str) -> bool:
        """Verify password"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def is_locked(self) -> bool:
        """Check if account is currently locked"""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until

    def record_failed_login(self, lockout_threshold: int = 5, lockout_duration_minutes: int = 15):
        """Record a failed login attempt, lock if threshold exceeded"""
        now = datetime.utcnow()
        # Reset counter if last failure was more than lockout duration ago
        if self.failed_login_at:
            from datetime import timedelta
            if now - self.failed_login_at > timedelta(minutes=lockout_duration_minutes):
                self.failed_login_count = 0

        self.failed_login_count = (self.failed_login_count or 0) + 1
        self.failed_login_at = now

        if self.failed_login_count >= lockout_threshold:
            from datetime import timedelta
            self.locked_until = now + timedelta(minutes=lockout_duration_minutes)

    def clear_failed_logins(self):
        """Clear failed login counter on successful login"""
        self.failed_login_count = 0
        self.failed_login_at = None
        self.locked_until = None

    def to_dict(self) -> dict:
        """Convert to dictionary (excluding sensitive data)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'auth_provider': self.auth_provider,
            'is_active': self.is_active,
            'is_locked': self.is_locked(),
            'failed_login_count': self.failed_login_count or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'password_changed_at': self.password_changed_at.isoformat() if self.password_changed_at else None,
            'display_name': self.display_name,
            'must_change_password': self.must_change_password or False,
        }

    def __repr__(self):
        return f'<User {self.username}>'


class AuditLog(db.Model):
    """Audit log for security events"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    username = db.Column(db.String(80), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support
    details = db.Column(db.Text, nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f'<AuditLog {self.action} by {self.username}>'


class OIDCProvider(db.Model):
    """OIDC Identity Provider configuration"""
    __tablename__ = 'oidc_providers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(200), nullable=True)

    # OIDC Configuration
    issuer = db.Column(db.String(500), nullable=False)
    client_id = db.Column(db.String(256), nullable=False)
    client_secret = db.Column(db.String(512), nullable=False)

    # Endpoints (auto-discovered from .well-known or manually set)
    authorization_endpoint = db.Column(db.String(500), nullable=True)
    token_endpoint = db.Column(db.String(500), nullable=True)
    userinfo_endpoint = db.Column(db.String(500), nullable=True)
    jwks_uri = db.Column(db.String(500), nullable=True)
    end_session_endpoint = db.Column(db.String(500), nullable=True)

    # Scopes and claims
    scopes = db.Column(db.String(500), default='openid profile email')

    # Role mapping (JSON stored as text)
    role_mapping = db.Column(db.Text, nullable=True)  # JSON: {"admin": ["admin-group"], ...}
    default_role = db.Column(db.String(20), default='viewer')

    # Status
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<OIDCProvider {self.name}>'
