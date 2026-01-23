"""
Authentication and user management for Wingman
Supports SQLAlchemy database backend with OIDC SSO integration
"""

import os
import bcrypt
import logging
from typing import Optional, Dict, List
from datetime import datetime
from functools import wraps
from flask import session, request, jsonify, current_app

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages authentication and user accounts using SQLAlchemy"""

    def __init__(self, app=None):
        self.app = app
        env_value = os.environ.get('ENABLE_AUTH', 'true')
        self.auth_enabled = env_value.lower() == 'true'
        self.oidc_enabled = os.environ.get('ENABLE_OIDC', 'false').lower() == 'true'
        logger.info(f"AuthManager initialized: ENABLE_AUTH={env_value}, auth_enabled={self.auth_enabled}")

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app context"""
        self.app = app
        with app.app_context():
            self._ensure_admin_exists()

    def _get_db(self):
        """Get database session from current app context"""
        from models import db
        return db

    def _get_user_model(self):
        """Get User model"""
        from models import User
        return User

    def _get_audit_model(self):
        """Get AuditLog model"""
        from models import AuditLog
        return AuditLog

    def _ensure_admin_exists(self):
        """Ensure at least one admin user exists"""
        try:
            if not self.auth_enabled:
                return

            User = self._get_user_model()
            admin_count = User.query.filter_by(role='admin', is_active=True).count()

            if admin_count == 0:
                # Create initial admin only if explicitly configured
                default_password = os.environ.get('ADMIN_PASSWORD')
                if not default_password:
                    logger.warning('No admin users exist and ADMIN_PASSWORD not set - skipping bootstrap')
                    return
                if len(default_password) < 14:
                    raise RuntimeError('ADMIN_PASSWORD must be at least 14 characters')

                result = self.create_user('admin', default_password, 'admin', 'admin@localhost')
                if result.get('success'):
                    logger.warning('=' * 60)
                    logger.warning("CREATED INITIAL ADMIN USER 'admin' - CHANGE PASSWORD IMMEDIATELY!")
                    logger.warning('Password was NOT logged for security.')
                    logger.warning('=' * 60)
                else:
                    logger.error("Failed to create initial admin user: %s" % result.get('error'))
        except Exception as e:
            logger.error(f"Error in _ensure_admin_exists: {e}")
            import traceback
            traceback.print_exc()

    def create_user(self, username: str, password: str, role: str, email: str = None,
                    skip_password_validation: bool = False) -> Dict:
        """Create a new user"""
        try:
            from security import validate_password

            db = self._get_db()
            User = self._get_user_model()

            # Check if user exists
            if User.query.filter_by(username=username).first():
                return {'success': False, 'error': 'User already exists'}

            if role not in ['admin', 'operator', 'viewer']:
                return {'success': False, 'error': 'Invalid role. Must be: admin, operator, or viewer'}

            # Validate password strength (skip for initial admin bootstrap)
            if not skip_password_validation:
                is_valid, errors = validate_password(password, username)
                if not is_valid:
                    return {'success': False, 'error': errors[0], 'password_errors': errors}

            # Create user
            user = User(
                username=username,
                email=email,
                role=role,
                auth_provider='local'
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            self._audit_log('user_created', username, f"User {username} created with role {role}")
            return {'success': True, 'message': f'User {username} created successfully'}
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username and password"""
        try:
            from security import get_lockout_policy

            db = self._get_db()
            User = self._get_user_model()
            lockout_policy = get_lockout_policy()

            user = User.query.filter_by(username=username).first()
            if not user:
                self._audit_log('login_failed', username, 'User not found')
                return None

            if not user.is_active:
                self._audit_log('login_failed', username, 'Account inactive')
                return None

            # Check if account is locked
            if user.is_locked():
                remaining = (user.locked_until - datetime.utcnow()).seconds // 60 + 1
                self._audit_log('login_failed', username, f'Account locked ({remaining} min remaining)')
                return {
                    '__locked': True,
                    'error': f'Account is locked. Try again in {remaining} minutes.',
                    'locked_until': user.locked_until.isoformat()
                }

            if user.check_password(password):
                # Clear failed login counter on success
                user.clear_failed_logins()
                user.last_login = datetime.utcnow()
                db.session.commit()
                self._audit_log('login_success', username, 'Successful login')

                # Return user dict with session_version for session tracking
                user_dict = user.to_dict()
                user_dict['session_version'] = user.session_version
                return user_dict
            else:
                # Record failed login attempt
                user.record_failed_login(
                    lockout_threshold=lockout_policy['threshold'],
                    lockout_duration_minutes=lockout_policy['duration_minutes']
                )
                db.session.commit()

                attempts_remaining = lockout_policy['threshold'] - user.failed_login_count
                if user.is_locked():
                    self._audit_log('account_locked', username,
                                    f'Account locked after {lockout_policy["threshold"]} failed attempts')
                else:
                    self._audit_log('login_failed', username,
                                    f'Invalid password ({attempts_remaining} attempts remaining)')
                return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    def change_password(self, username: str, old_password: str, new_password: str) -> Dict:
        """Change user password"""
        try:
            from security import validate_password

            db = self._get_db()
            User = self._get_user_model()

            user = User.query.filter_by(username=username).first()
            if not user:
                return {'success': False, 'error': 'User not found'}

            if not user.check_password(old_password):
                self._audit_log('password_change_failed', username, 'Invalid old password')
                return {'success': False, 'error': 'Invalid old password'}

            # Validate new password strength
            is_valid, errors = validate_password(new_password, username)
            if not is_valid:
                return {'success': False, 'error': errors[0], 'password_errors': errors}

            user.set_password(new_password)
            db.session.commit()

            self._audit_log('password_changed', username, 'Password changed successfully')
            return {
                'success': True,
                'message': 'Password changed successfully',
                'session_invalidated': True  # Signal to client to re-login
            }
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def delete_user(self, username: str) -> Dict:
        """Delete a user"""
        try:
            db = self._get_db()
            User = self._get_user_model()

            user = User.query.filter_by(username=username).first()
            if not user:
                return {'success': False, 'error': 'User not found'}

            # Prevent deleting last admin
            if user.role == 'admin':
                admin_count = User.query.filter_by(role='admin', is_active=True).count()
                if admin_count <= 1:
                    return {'success': False, 'error': 'Cannot delete the last admin user'}

            db.session.delete(user)
            db.session.commit()

            self._audit_log('user_deleted', username, f'User {username} deleted')
            return {'success': True, 'message': f'User {username} deleted successfully'}
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def list_users(self) -> List[Dict]:
        """List all users (excluding password hashes)"""
        try:
            User = self._get_user_model()
            users = User.query.all()
            return [user.to_dict() for user in users]
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []

    def update_user_role(self, username: str, new_role: str) -> Dict:
        """Update user role"""
        try:
            db = self._get_db()
            User = self._get_user_model()

            user = User.query.filter_by(username=username).first()
            if not user:
                return {'success': False, 'error': 'User not found'}

            if new_role not in ['admin', 'operator', 'viewer']:
                return {'success': False, 'error': 'Invalid role'}

            old_role = user.role

            # Prevent demoting last admin
            if old_role == 'admin' and new_role != 'admin':
                admin_count = User.query.filter_by(role='admin', is_active=True).count()
                if admin_count <= 1:
                    return {'success': False, 'error': 'Cannot change role of the last admin user'}

            user.role = new_role
            db.session.commit()

            self._audit_log('role_changed', username, f'Role changed from {old_role} to {new_role}')
            return {'success': True, 'message': f'User role updated to {new_role}'}
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def update_user_status(self, username: str, is_active: bool) -> Dict:
        """Update user active status"""
        try:
            db = self._get_db()
            User = self._get_user_model()

            user = User.query.filter_by(username=username).first()
            if not user:
                return {'success': False, 'error': 'User not found'}

            # Prevent deactivating last admin
            if not is_active and user.role == 'admin':
                active_admin_count = User.query.filter_by(role='admin', is_active=True).count()
                if active_admin_count <= 1:
                    return {'success': False, 'error': 'Cannot deactivate the last active admin user'}

            user.is_active = is_active
            db.session.commit()

            action = 'activated' if is_active else 'deactivated'
            self._audit_log('user_status_changed', username, f'User {action}')
            return {'success': True, 'message': f'User {action} successfully'}
        except Exception as e:
            logger.error(f"Error updating user status: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def reset_user_password(self, username: str, new_password: str) -> Dict:
        """Reset user password (admin action)"""
        try:
            from security import validate_password

            db = self._get_db()
            User = self._get_user_model()

            user = User.query.filter_by(username=username).first()
            if not user:
                return {'success': False, 'error': 'User not found'}

            # Validate new password strength
            is_valid, errors = validate_password(new_password, username)
            if not is_valid:
                return {'success': False, 'error': errors[0], 'password_errors': errors}

            user.set_password(new_password)
            db.session.commit()

            self._audit_log('password_reset', username, 'Password reset by admin')
            return {'success': True, 'message': 'Password reset successfully'}
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def unlock_user(self, username: str) -> Dict:
        """Unlock a locked user account (admin action)"""
        try:
            db = self._get_db()
            User = self._get_user_model()

            user = User.query.filter_by(username=username).first()
            if not user:
                return {'success': False, 'error': 'User not found'}

            user.clear_failed_logins()
            db.session.commit()

            self._audit_log('account_unlocked', username, 'Account unlocked by admin')
            return {'success': True, 'message': f'User {username} unlocked successfully'}
        except Exception as e:
            logger.error(f"Error unlocking user: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def get_user(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        try:
            User = self._get_user_model()
            user = User.query.filter_by(username=username).first()
            return user.to_dict() if user else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def get_user_by_external_id(self, external_id: str, provider: str = 'oidc') -> Optional[Dict]:
        """Get user by external ID (for SSO)"""
        try:
            User = self._get_user_model()
            user = User.query.filter_by(external_id=external_id, auth_provider=provider).first()
            return user.to_dict() if user else None
        except Exception as e:
            logger.error(f"Error getting user by external ID: {e}")
            return None

    def create_or_update_sso_user(self, external_id: str, username: str, email: str,
                                   role: str, provider: str = 'oidc',
                                   display_name: str = None) -> Optional[Dict]:
        """Create or update SSO user (JIT provisioning)"""
        try:
            db = self._get_db()
            User = self._get_user_model()

            # Look for existing user by external_id
            user = User.query.filter_by(external_id=external_id, auth_provider=provider).first()

            if not user:
                # Try to find by email and link accounts
                if email:
                    user = User.query.filter_by(email=email).first()
                    if user and user.auth_provider == 'local':
                        # Link existing local user to SSO
                        user.external_id = external_id
                        user.auth_provider = provider

            if not user:
                # Create new user
                user = User(
                    username=self._generate_unique_username(username),
                    email=email,
                    external_id=external_id,
                    auth_provider=provider,
                    role=role,
                    display_name=display_name
                )
                db.session.add(user)

            # Update user info on each login
            if display_name:
                user.display_name = display_name
            if email:
                user.email = email
            user.role = role
            user.last_login = datetime.utcnow()

            db.session.commit()
            self._audit_log('sso_login', user.username, f'SSO login via {provider}')

            return user.to_dict()
        except Exception as e:
            logger.error(f"Error creating/updating SSO user: {e}")
            db.session.rollback()
            return None

    def _generate_unique_username(self, base_username: str) -> str:
        """Generate unique username"""
        import re
        User = self._get_user_model()

        # Sanitize
        base_username = re.sub(r'[^a-zA-Z0-9_-]', '_', base_username)
        if not base_username:
            base_username = 'user'

        # Ensure uniqueness
        username = base_username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}_{counter}"
            counter += 1

        return username

    def _audit_log(self, action: str, username: str, details: str):
        """Log authentication events for audit trail"""
        try:
            db = self._get_db()
            AuditLog = self._get_audit_model()

            ip_address = request.remote_addr if request else 'unknown'
            user_agent = request.user_agent.string if request and request.user_agent else None

            log_entry = AuditLog(
                action=action,
                username=username,
                ip_address=ip_address,
                details=details,
                user_agent=user_agent
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error writing audit log: {e}")
            # Don't fail the main operation if audit logging fails
            try:
                db.session.rollback()
            except:
                pass


# Flask decorators for route protection
def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if auth is enabled
        auth_enabled = os.environ.get('ENABLE_AUTH', 'true').lower() == 'true'
        wingman_env = os.environ.get('WINGMAN_ENV', 'prod').lower()
        # Fail-closed outside dev: never silently bypass access control
        if not auth_enabled and wingman_env != 'dev':
            return jsonify({'success': False, 'error': 'Authentication disabled'}), 503
        if not auth_enabled:
            return f(*args, **kwargs)

        # Check if user is logged in
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if auth is enabled
            auth_enabled = os.environ.get('ENABLE_AUTH', 'true').lower() == 'true'
            wingman_env = os.environ.get('WINGMAN_ENV', 'prod').lower()
            # Fail-closed outside dev: never silently bypass access control
            if not auth_enabled and wingman_env != 'dev':
                return jsonify({'success': False, 'error': 'Authentication disabled'}), 503
            if not auth_enabled:
                return f(*args, **kwargs)

            # Check if user is logged in
            if 'username' not in session:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401

            # Check role
            user_role = session.get('role')
            if user_role not in allowed_roles:
                return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator
