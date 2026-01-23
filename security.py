"""
Security utilities for Wingman
Password validation, security headers, and other security functions
"""

import re
import os
from typing import Tuple, List
from functools import wraps
from flask import session, request, jsonify


# =============================================================================
# Password Policy Configuration (via environment variables)
# =============================================================================

def get_password_policy():
    """Get password policy from environment variables"""
    return {
        'min_length': int(os.environ.get('PASSWORD_MIN_LENGTH', '12')),
        'require_uppercase': os.environ.get('PASSWORD_REQUIRE_UPPERCASE', 'true').lower() == 'true',
        'require_lowercase': os.environ.get('PASSWORD_REQUIRE_LOWERCASE', 'true').lower() == 'true',
        'require_digit': os.environ.get('PASSWORD_REQUIRE_DIGIT', 'true').lower() == 'true',
        'require_special': os.environ.get('PASSWORD_REQUIRE_SPECIAL', 'true').lower() == 'true',
        'special_chars': os.environ.get('PASSWORD_SPECIAL_CHARS', '!@#$%^&*()_+-=[]{}|;:,.<>?'),
    }


def validate_password(password: str, username: str = None) -> Tuple[bool, List[str]]:
    """
    Validate password against security policy.

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    policy = get_password_policy()

    # Length check
    if len(password) < policy['min_length']:
        errors.append(f"Password must be at least {policy['min_length']} characters long")

    # Uppercase check
    if policy['require_uppercase'] and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    # Lowercase check
    if policy['require_lowercase'] and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")

    # Digit check
    if policy['require_digit'] and not re.search(r'\d', password):
        errors.append("Password must contain at least one number")

    # Special character check
    if policy['require_special']:
        special_pattern = f'[{re.escape(policy["special_chars"])}]'
        if not re.search(special_pattern, password):
            errors.append(f"Password must contain at least one special character ({policy['special_chars'][:10]}...)")

    # Username similarity check (prevent password containing username)
    if username and len(username) >= 3:
        if username.lower() in password.lower():
            errors.append("Password cannot contain your username")

    # Common password check (basic list - can be expanded)
    common_passwords = {
        'password', 'password123', '123456', '12345678', 'qwerty', 'abc123',
        'monkey', 'letmein', 'dragon', 'master', 'admin', 'welcome',
        'login', 'passw0rd', 'password1', 'admin123', 'root', 'toor'
    }
    if password.lower() in common_passwords:
        errors.append("Password is too common. Please choose a stronger password")

    return len(errors) == 0, errors


def get_password_requirements() -> dict:
    """Get human-readable password requirements for display"""
    policy = get_password_policy()
    requirements = [f"At least {policy['min_length']} characters"]

    if policy['require_uppercase']:
        requirements.append("At least one uppercase letter (A-Z)")
    if policy['require_lowercase']:
        requirements.append("At least one lowercase letter (a-z)")
    if policy['require_digit']:
        requirements.append("At least one number (0-9)")
    if policy['require_special']:
        requirements.append(f"At least one special character")

    return {
        'min_length': policy['min_length'],
        'require_uppercase': policy['require_uppercase'],
        'require_lowercase': policy['require_lowercase'],
        'require_digit': policy['require_digit'],
        'require_special': policy['require_special'],
        'requirements_text': requirements
    }


# =============================================================================
# Account Lockout Configuration
# =============================================================================

def get_lockout_policy():
    """Get account lockout policy from environment variables"""
    return {
        'threshold': int(os.environ.get('LOCKOUT_THRESHOLD', '5')),
        'duration_minutes': int(os.environ.get('LOCKOUT_DURATION_MINUTES', '15')),
    }


# =============================================================================
# Session Security Configuration
# =============================================================================

def get_session_policy():
    """Get session security policy from environment variables"""
    return {
        'timeout_minutes': int(os.environ.get('SESSION_TIMEOUT_MINUTES', '60')),
        'absolute_timeout_hours': int(os.environ.get('SESSION_ABSOLUTE_TIMEOUT_HOURS', '24')),
    }


# =============================================================================
# Security Headers
# =============================================================================

def get_security_headers() -> dict:
    """
    Get security headers to add to all responses.
    Configure via environment variables for flexibility.
    """
    # Default CSP - restrictive but functional
    default_csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.socket.io https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self' wss: ws:; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "base-uri 'self';"
    )

    headers = {
        # Prevent clickjacking
        'X-Frame-Options': os.environ.get('X_FRAME_OPTIONS', 'DENY'),

        # Prevent MIME type sniffing
        'X-Content-Type-Options': 'nosniff',

        # XSS Protection (legacy, but still useful for older browsers)
        'X-XSS-Protection': '1; mode=block',

        # Referrer Policy
        'Referrer-Policy': os.environ.get('REFERRER_POLICY', 'strict-origin-when-cross-origin'),

        # Content Security Policy
        'Content-Security-Policy': os.environ.get('CONTENT_SECURITY_POLICY', default_csp),

        # Permissions Policy (formerly Feature-Policy)
        'Permissions-Policy': os.environ.get(
            'PERMISSIONS_POLICY',
            'geolocation=(), microphone=(), camera=(), payment=()'
        ),
    }

    # HSTS - only enable if explicitly configured (requires HTTPS)
    hsts_enabled = os.environ.get('ENABLE_HSTS', 'false').lower() == 'true'
    if hsts_enabled:
        max_age = os.environ.get('HSTS_MAX_AGE', '31536000')  # 1 year
        headers['Strict-Transport-Security'] = f'max-age={max_age}; includeSubDomains'

    return headers


def apply_security_headers(response):
    """Apply security headers to a Flask response"""
    for header, value in get_security_headers().items():
        response.headers[header] = value
    return response


# =============================================================================
# Session Validation Decorator
# =============================================================================

def validate_session(f):
    """
    Decorator to validate session is still valid.
    Checks session version matches user's current session version.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from models import User

        if 'username' not in session:
            return f(*args, **kwargs)

        # Check session version
        session_version = session.get('session_version')
        username = session.get('username')

        if username and session_version is not None:
            user = User.query.filter_by(username=username).first()
            if user and user.session_version != session_version:
                # Session invalidated (password changed, etc.)
                session.clear()
                return jsonify({
                    'success': False,
                    'error': 'Session expired. Please log in again.',
                    'code': 'SESSION_INVALIDATED'
                }), 401

        return f(*args, **kwargs)
    return decorated_function
