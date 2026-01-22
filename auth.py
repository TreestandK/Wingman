"""
Authentication and user management for Wingman
Supports both built-in authentication and optional SAML integration
"""

import os
import json
import bcrypt
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, jsonify

logger = logging.getLogger(__name__)

class User:
    """User model"""
    def __init__(self, username: str, password_hash: str, role: str, email: str = None, created_at: str = None):
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.email = email
        self.created_at = created_at or datetime.now().isoformat()
        self.last_login = None
        self.is_active = True

    def to_dict(self):
        """Convert to dictionary (excluding password_hash)"""
        return {
            'username': self.username,
            'role': self.role,
            'email': self.email,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'is_active': self.is_active
        }

    def check_password(self, password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


class AuthManager:
    """Manages authentication and user accounts"""

    def __init__(self, data_dir: str = '/app/data'):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, 'users.json')
        self.audit_log_file = os.path.join(data_dir, 'audit.log')
        self.users: Dict[str, User] = {}
        self.auth_enabled = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'
        self.saml_enabled = os.environ.get('ENABLE_SAML', 'false').lower() == 'true'
        self._load_users()
        self._ensure_admin_exists()

    def _load_users(self):
        """Load users from JSON file"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    for username, data in users_data.items():
                        self.users[username] = User(
                            username=data['username'],
                            password_hash=data['password_hash'],
                            role=data['role'],
                            email=data.get('email'),
                            created_at=data.get('created_at')
                        )
                        self.users[username].last_login = data.get('last_login')
                        self.users[username].is_active = data.get('is_active', True)
                logger.info(f"Loaded {len(self.users)} users from {self.users_file}")
        except Exception as e:
            logger.error(f"Error loading users: {e}")

    def _save_users(self):
        """Save users to JSON file"""
        try:
            users_data = {}
            for username, user in self.users.items():
                users_data[username] = {
                    'username': user.username,
                    'password_hash': user.password_hash,
                    'role': user.role,
                    'email': user.email,
                    'created_at': user.created_at,
                    'last_login': user.last_login,
                    'is_active': user.is_active
                }
            with open(self.users_file, 'w') as f:
                json.dump(users_data, f, indent=2)
            logger.info(f"Saved {len(self.users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Error saving users: {e}")

    def _ensure_admin_exists(self):
        """Ensure at least one admin user exists"""
        try:
            if not self.users and self.auth_enabled:
                # Create default admin with password from env or default
                default_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                result = self.create_user('admin', default_password, 'admin', 'admin@localhost')
                if result.get('success'):
                    logger.warning("=" * 60)
                    logger.warning("CREATED DEFAULT ADMIN USER - CHANGE PASSWORD IMMEDIATELY!")
                    logger.warning(f"Username: admin")
                    logger.warning(f"Password: {default_password}")
                    logger.warning("Run: docker exec -it <container> python create_admin.py")
                    logger.warning("=" * 60)
                else:
                    logger.error(f"Failed to create default admin user: {result.get('error')}")
        except Exception as e:
            logger.error(f"Error in _ensure_admin_exists: {e}")
            # Don't crash the app, just log the error
            import traceback
            traceback.print_exc()

    def create_user(self, username: str, password: str, role: str, email: str = None) -> Dict:
        """Create a new user"""
        try:
            if username in self.users:
                return {'success': False, 'error': 'User already exists'}

            if role not in ['admin', 'operator', 'viewer']:
                return {'success': False, 'error': 'Invalid role. Must be: admin, operator, or viewer'}

            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Create user
            user = User(username, password_hash, role, email)
            self.users[username] = user
            self._save_users()

            self._audit_log('user_created', username, f"User {username} created with role {role}")
            return {'success': True, 'message': f'User {username} created successfully'}
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return {'success': False, 'error': str(e)}

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        try:
            user = self.users.get(username)
            if not user:
                self._audit_log('login_failed', username, 'User not found')
                return None

            if not user.is_active:
                self._audit_log('login_failed', username, 'Account inactive')
                return None

            if user.check_password(password):
                user.last_login = datetime.now().isoformat()
                self._save_users()
                self._audit_log('login_success', username, 'Successful login')
                return user
            else:
                self._audit_log('login_failed', username, 'Invalid password')
                return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    def change_password(self, username: str, old_password: str, new_password: str) -> Dict:
        """Change user password"""
        try:
            user = self.users.get(username)
            if not user:
                return {'success': False, 'error': 'User not found'}

            if not user.check_password(old_password):
                self._audit_log('password_change_failed', username, 'Invalid old password')
                return {'success': False, 'error': 'Invalid old password'}

            # Hash new password
            user.password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            self._save_users()

            self._audit_log('password_changed', username, 'Password changed successfully')
            return {'success': True, 'message': 'Password changed successfully'}
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return {'success': False, 'error': str(e)}

    def delete_user(self, username: str) -> Dict:
        """Delete a user"""
        try:
            if username not in self.users:
                return {'success': False, 'error': 'User not found'}

            # Prevent deleting last admin
            if self.users[username].role == 'admin':
                admin_count = sum(1 for u in self.users.values() if u.role == 'admin' and u.is_active)
                if admin_count <= 1:
                    return {'success': False, 'error': 'Cannot delete the last admin user'}

            del self.users[username]
            self._save_users()
            self._audit_log('user_deleted', username, f'User {username} deleted')
            return {'success': True, 'message': f'User {username} deleted successfully'}
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return {'success': False, 'error': str(e)}

    def list_users(self) -> List[Dict]:
        """List all users (excluding password hashes)"""
        return [user.to_dict() for user in self.users.values()]

    def update_user_role(self, username: str, new_role: str) -> Dict:
        """Update user role"""
        try:
            if username not in self.users:
                return {'success': False, 'error': 'User not found'}

            if new_role not in ['admin', 'operator', 'viewer']:
                return {'success': False, 'error': 'Invalid role'}

            old_role = self.users[username].role

            # Prevent demoting last admin
            if old_role == 'admin' and new_role != 'admin':
                admin_count = sum(1 for u in self.users.values() if u.role == 'admin' and u.is_active)
                if admin_count <= 1:
                    return {'success': False, 'error': 'Cannot change role of the last admin user'}

            self.users[username].role = new_role
            self._save_users()
            self._audit_log('role_changed', username, f'Role changed from {old_role} to {new_role}')
            return {'success': True, 'message': f'User role updated to {new_role}'}
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            return {'success': False, 'error': str(e)}

    def _audit_log(self, action: str, username: str, details: str):
        """Log authentication events for audit trail"""
        try:
            timestamp = datetime.now().isoformat()
            ip_address = request.remote_addr if request else 'unknown'
            log_entry = f"{timestamp} | {action} | {username} | {ip_address} | {details}\n"

            with open(self.audit_log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Error writing audit log: {e}")


# Flask decorators for route protection
def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if auth is enabled
        auth_enabled = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'
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
            auth_enabled = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'
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
