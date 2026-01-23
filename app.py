#!/usr/bin/env python3
"""
Wingman Game Server Manager - Web Interface
Flask application for managing game server deployments
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import json
import logging
import hmac
import secrets
from datetime import datetime, timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from deployment_manager import DeploymentManager
from auth import AuthManager, login_required, role_required
from errors import WingmanError, handle_api_error
from models import db, User, AuditLog, OIDCProvider
from oidc import oidc_manager, oauth

app = Flask(__name__)

# Deployment mode: dev vs prod (default prod)
WINGMAN_ENV = os.environ.get('WINGMAN_ENV', 'prod').lower()
AUTH_ENABLED = os.environ.get('ENABLE_AUTH', 'true').lower() == 'true'

# Fail-closed: never allow auth to be disabled outside dev
if WINGMAN_ENV != 'dev' and not AUTH_ENABLED:
    raise RuntimeError('ENABLE_AUTH=false is not allowed when WINGMAN_ENV != dev')

secret = os.environ.get('FLASK_SECRET_KEY')
if not secret or len(secret) < 32:
    raise RuntimeError('FLASK_SECRET_KEY must be set to a strong random value (>=32 chars)')
app.secret_key = secret

# Trust proxy headers from the immediate upstream (Nginx/Cloudflare)
# Ensure your proxy sets X-Forwarded-For / X-Forwarded-Proto / X-Forwarded-Host.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Initialize SocketIO for real-time deployment logs
allowed = os.environ.get('WINGMAN_ALLOWED_ORIGINS', '')
allowed_origins = [o.strip() for o in allowed.split(',') if o.strip()]
# If empty, restrict to same-origin.
socketio = SocketIO(app, cors_allowed_origins=allowed_origins or None, async_mode='eventlet')

# Session cookie hardening (set SESSION_COOKIE_SECURE=true when behind HTTPS)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    # Same-origin app; Lax supports common SSO flows (OIDC/SAML redirects).
    SESSION_COOKIE_SAMESITE=os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax' if WINGMAN_ENV != 'dev' else 'Lax'),
    # Default to Secure in non-dev; override only for local development.
    SESSION_COOKIE_SECURE=(os.environ.get('SESSION_COOKIE_SECURE', 'true' if WINGMAN_ENV != 'dev' else 'false').lower() == 'true'),
)

# Database configuration
# Use /app/data for Docker, data/ for local development
if os.path.exists('/app/data'):
    default_db_path = '/app/data/wingman.db'
else:
    # Local development - use absolute path relative to this file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    default_db_path = os.path.join(data_dir, 'wingman.db')

db_url = os.environ.get('DATABASE_URL', f'sqlite:///{default_db_path}')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure data directory exists for SQLite (for custom DATABASE_URL)
if db_url.startswith('sqlite:///'):
    db_file = db_url.replace('sqlite:///', '')
    db_dir = os.path.dirname(db_file)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

# Initialize SQLAlchemy
db.init_app(app)

# Create tables on startup (if they don't exist)
with app.app_context():
    db.create_all()

# Basic rate limiting (tune as needed)
limiter = Limiter(get_remote_address, app=app, default_limits=['200 per minute'])

# Configure logging - use local directory if /app/logs doesn't exist
log_dir = '/app/logs' if os.path.exists('/app/logs') else 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'wingman.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize managers
deployment_manager = DeploymentManager()
auth_manager = AuthManager(app)

# --- CSRF protection for cookie-based sessions ---
# If a request uses Authorization: Bearer <token>, it is treated as an API-token request and is exempt.
# Browser/session-authenticated state-changing requests must include X-CSRF-Token.

def _ensure_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']

@app.route('/api/csrf', methods=['GET'])
@login_required
def get_csrf_token():
    return jsonify({'success': True, 'csrf_token': _ensure_csrf_token()})

@app.before_request
def enforce_csrf_for_cookie_sessions():
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        auth = request.headers.get('Authorization', '')
        if auth.lower().startswith('bearer '):
            return  # API token auth: CSRF not applicable
        # If using session cookies, require CSRF token
        # Allow login/logout routes to proceed without CSRF to avoid bootstrapping issues.
        if request.path in ('/login', '/api/auth/login') or request.path.startswith('/static/'):
            return
        expected = session.get('csrf_token')
        provided = request.headers.get('X-CSRF-Token') or request.headers.get('X-CSRFToken')
        if not expected or not provided or not hmac.compare_digest(str(expected), str(provided)):
            return jsonify({'success': False, 'error': 'CSRF token missing or invalid'}), 403


# Add cache-control headers and security headers to all responses
@app.after_request
def add_header(response):
    """Add cache control and security headers to responses"""
    from security import apply_security_headers

    # Prevent caching of HTML pages (fixes Firefox caching issues)
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    # Apply security headers to all responses
    apply_security_headers(response)

    return response


# Session timeout and validation
@app.before_request
def check_session_timeout():
    """Check if session has timed out"""
    from security import get_session_policy

    # Skip for unauthenticated routes
    if 'username' not in session:
        return

    # Skip for static files and health checks
    if request.path.startswith('/static/') or request.path == '/health':
        return

    session_policy = get_session_policy()
    now = datetime.utcnow()

    # Check absolute timeout (max session lifetime)
    login_time_str = session.get('login_time')
    if login_time_str:
        login_time = datetime.fromisoformat(login_time_str)
        max_lifetime = timedelta(hours=session_policy['absolute_timeout_hours'])
        if now - login_time > max_lifetime:
            username = session.get('username', 'unknown')
            session.clear()
            logger.info(f"Session expired (absolute timeout) for user {username}")
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Session expired. Please log in again.',
                    'code': 'SESSION_EXPIRED'
                }), 401
            return redirect(url_for('login'))

    # Check inactivity timeout
    last_activity_str = session.get('last_activity')
    if last_activity_str:
        last_activity = datetime.fromisoformat(last_activity_str)
        inactivity_timeout = timedelta(minutes=session_policy['timeout_minutes'])
        if now - last_activity > inactivity_timeout:
            username = session.get('username', 'unknown')
            session.clear()
            logger.info(f"Session expired (inactivity timeout) for user {username}")
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Session expired due to inactivity. Please log in again.',
                    'code': 'SESSION_TIMEOUT'
                }), 401
            return redirect(url_for('login'))

    # Check session version (password changed, etc.)
    username = session.get('username')
    session_version = session.get('session_version')
    if username and session_version is not None:
        user = User.query.filter_by(username=username).first()
        if user and user.session_version != session_version:
            session.clear()
            logger.info(f"Session invalidated (password changed) for user {username}")
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Session invalidated. Please log in again.',
                    'code': 'SESSION_INVALIDATED'
                }), 401
            return redirect(url_for('login'))

    # Update last activity timestamp
    session['last_activity'] = now.isoformat()

@app.route('/')
def index():
    """Main dashboard - redirect to login if auth enabled and not authenticated"""
    logger.info(f"Index route accessed: auth_enabled={auth_manager.auth_enabled}, username_in_session={'username' in session}")
    if auth_manager.auth_enabled and 'username' not in session:
        logger.info("Redirecting to login page")
        return redirect(url_for('login'))
    logger.info("Serving index.html")
    response = render_template('index.html')
    # Prevent caching of authenticated pages
    return response, 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

@app.route('/login', methods=['GET'])
def login():
    """Login page"""
    if not auth_manager.auth_enabled:
        return redirect(url_for('index'))
    if 'username' in session:
        return redirect(url_for('index'))
    response = render_template('login.html')
    # Prevent caching of login page
    return response, 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def api_login():
    """Authenticate user"""
    try:
        from security import get_session_policy

        if not auth_manager.auth_enabled:
            return jsonify({'success': False, 'error': 'Authentication not enabled'}), 400

        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400

        user = auth_manager.authenticate(username, password)

        # Handle account lockout response
        if user and user.get('__locked'):
            return jsonify({
                'success': False,
                'error': user.get('error'),
                'locked': True,
                'locked_until': user.get('locked_until')
            }), 423  # 423 Locked

        if user:
            # Set session data
            session['username'] = user['username']
            session['role'] = user['role']
            session['auth_provider'] = 'local'
            session['session_version'] = user.get('session_version', 0)

            # Set session timestamps for timeout tracking
            session_policy = get_session_policy()
            now = datetime.utcnow()
            session['login_time'] = now.isoformat()
            session['last_activity'] = now.isoformat()

            csrf_token = _ensure_csrf_token()
            logger.info(f"User {username} logged in successfully")
            return jsonify({
                'success': True,
                'user': user,
                'csrf_token': csrf_token
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Logout user"""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"User {username} logged out")
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Get authentication status"""
    # Log current state for debugging
    logger.info(f"auth_status called: auth_manager.auth_enabled={auth_manager.auth_enabled}, ENABLE_AUTH env={os.environ.get('ENABLE_AUTH', 'NOT SET')}")

    return jsonify({
        'success': True,
        'auth_enabled': auth_manager.auth_enabled,
        'authenticated': 'username' in session,
        'user': {
            'username': session.get('username'),
            'role': session.get('role')
        } if 'username' in session else None
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/api/auth/password-requirements', methods=['GET'])
def get_password_requirements():
    """Get password requirements for display to users"""
    from security import get_password_requirements
    return jsonify({
        'success': True,
        'requirements': get_password_requirements()
    })


@app.route('/api/users/<username>/unlock', methods=['POST'])
@login_required
@role_required(['admin'])
def unlock_user(username):
    """Unlock a locked user account"""
    result = auth_manager.unlock_user(username)
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 400

# --- OIDC SSO Routes ---
# Initialize OIDC if enabled
OIDC_ENABLED = os.environ.get('ENABLE_OIDC', 'false').lower() == 'true'
if OIDC_ENABLED:
    oidc_manager.init_app(app)

@app.route('/api/auth/providers', methods=['GET'])
def get_auth_providers():
    """Get available authentication providers"""
    providers = [
        {
            'name': 'local',
            'display_name': 'Local Account',
            'type': 'local'
        }
    ]

    # Add OIDC providers if enabled
    if OIDC_ENABLED and oidc_manager.enabled:
        for provider in oidc_manager.get_providers():
            provider['login_url'] = url_for('oidc_login', provider=provider['name'])
            providers.append(provider)

    return jsonify({'success': True, 'providers': providers})

@app.route('/auth/oidc/login')
@app.route('/auth/oidc/login/<provider>')
def oidc_login(provider='default'):
    """Initiate OIDC login flow"""
    if not OIDC_ENABLED or not oidc_manager.enabled:
        return jsonify({'success': False, 'error': 'OIDC not enabled'}), 400

    try:
        auth_url, state = oidc_manager.get_authorization_url(provider)
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"OIDC login error: {e}")
        return redirect(url_for('login') + '?error=oidc_init_failed')

@app.route('/auth/oidc/callback')
@app.route('/auth/oidc/callback/<provider>')
def oidc_callback(provider='default'):
    """Handle OIDC callback"""
    if not OIDC_ENABLED or not oidc_manager.enabled:
        return redirect(url_for('login'))

    # Check for errors from provider
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', error)
        logger.error(f"OIDC error from provider: {error} - {error_desc}")
        return redirect(url_for('login') + f'?error={error}')

    # Handle callback
    user_info = oidc_manager.handle_callback(provider)

    if user_info:
        # Create or update user in database
        user = auth_manager.create_or_update_sso_user(
            external_id=user_info['external_id'],
            username=user_info['username'],
            email=user_info['email'],
            role=user_info['role'],
            provider='oidc',
            display_name=user_info.get('display_name')
        )

        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            session['auth_provider'] = 'oidc'
            _ensure_csrf_token()
            logger.info(f"OIDC user {user['username']} logged in via {provider}")
            return redirect(url_for('index'))

    logger.error("OIDC callback failed - no user info")
    return redirect(url_for('login') + '?error=oidc_failed')

@app.route('/auth/oidc/logout')
def oidc_logout():
    """OIDC logout"""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"OIDC user {username} logged out")
    return redirect(url_for('login'))

@app.route('/api/auth/debug', methods=['GET'])
@role_required(['admin'])
def auth_debug():
    """Debug endpoint to troubleshoot auth issues"""
    if os.environ.get('WINGMAN_DEBUG_ENDPOINTS', 'false').lower() != 'true':
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({
        'auth_manager': {
            'auth_enabled': auth_manager.auth_enabled,
            'auth_enabled_type': type(auth_manager.auth_enabled).__name__,
            'saml_enabled': auth_manager.saml_enabled,
            'users_count': len(auth_manager.users),
            'users': list(auth_manager.users.keys())
        },
        'environment': {
            'ENABLE_AUTH': os.environ.get('ENABLE_AUTH', 'NOT SET'),
            'ENABLE_SAML': os.environ.get('ENABLE_SAML', 'NOT SET'),
            'FLASK_SECRET_KEY_LENGTH': len(os.environ.get('FLASK_SECRET_KEY', ''))
        },
        'session': {
            'authenticated': 'username' in session,
            'username': session.get('username'),
            'role': session.get('role')
        },
        'auth_manager_id': id(auth_manager),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/config', methods=['GET'])
@role_required(['admin'])
@login_required
def get_config():
    """Get current configuration"""
    try:
        config = deployment_manager.get_config()
        # Mask secrets in response
        masked_config = mask_secrets(config)
        return jsonify({'success': True, 'config': masked_config})
    except Exception as e:
        logger.error(f"Configuration retrieval error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
@role_required(['admin'])
def save_config():
    """Save configuration settings"""
    try:
        config = request.json
        result = deployment_manager.save_config(config)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Configuration save error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/validate', methods=['POST'])
@role_required(['admin'])
def validate_config():
    """Validate configuration settings"""
    try:
        config = request.json
        validation_result = deployment_manager.validate_config(config)
        return jsonify(validation_result)
    except Exception as e:
        logger.error(f"Configuration validation error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config/test', methods=['POST'])
@role_required(['admin'])
def test_connectivity():
    """Test API connectivity"""
    try:
        # Use saved configuration to avoid SSRF via user-supplied URLs
        test_results = deployment_manager.test_api_connectivity()
        return jsonify(test_results)
    except Exception as e:
        logger.error(f"Connectivity test error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/templates', methods=['GET'])
@login_required
def list_templates():
    """List available deployment templates"""
    try:
        templates = deployment_manager.list_templates()
        return jsonify({'success': True, 'templates': templates})
    except Exception as e:
        logger.error(f"Template list error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/templates/<name>', methods=['GET'])
@login_required
def get_template(name):
    """Get a specific template"""
    try:
        template = deployment_manager.get_template(name)
        if template:
            return jsonify({'success': True, 'template': template})
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    except Exception as e:
        logger.error(f"Template get error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/templates', methods=['POST'])
@role_required(['admin'])
def save_template():
    """Save a deployment template"""
    try:
        template_data = request.json
        result = deployment_manager.save_template(template_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Template save error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/deploy', methods=['POST'])
@role_required(['admin','operator'])
def deploy_server():
    """Deploy a new game server"""
    try:
        deployment_config = request.json
        deployment_id = deployment_manager.start_deployment(deployment_config)
        return jsonify({
            'success': True,
            'deployment_id': deployment_id,
            'message': 'Deployment started'
        })
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/deploy/<deployment_id>/status', methods=['GET'])
@login_required
def deployment_status(deployment_id):
    """Get deployment status"""
    try:
        status = deployment_manager.get_deployment_status(deployment_id)
        if status:
            return jsonify({'success': True, 'status': status})
        return jsonify({'success': False, 'error': 'Deployment not found'}), 404
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/deployments', methods=['GET'])
@login_required
def list_deployments():
    """List all deployments"""
    try:
        deployments = deployment_manager.list_deployments()
        return jsonify({'success': True, 'deployments': deployments})
    except Exception as e:
        logger.error(f"Deployment list error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/deploy/<deployment_id>/rollback', methods=['POST'])
@role_required(['admin','operator'])
def rollback_deployment(deployment_id):
    """Rollback a deployment"""
    try:
        result = deployment_manager.rollback_deployment(deployment_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Rollback error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs/<deployment_id>', methods=['GET'])
@login_required
def get_deployment_logs(deployment_id):
    """Get deployment logs"""
    try:
        logs = deployment_manager.get_deployment_logs(deployment_id)
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        logger.error(f"Log retrieval error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/monitoring/stats', methods=['GET'])
@login_required
def get_monitoring_stats():
    """Get monitoring statistics"""
    try:
        stats = deployment_manager.get_monitoring_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Stats retrieval error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pterodactyl/nests', methods=['GET'])
@role_required(['admin','operator'])
def get_pterodactyl_nests():
    """Get Pterodactyl nests"""
    try:
        nests = deployment_manager.get_pterodactyl_nests()
        return jsonify({'success': True, 'nests': nests})
    except Exception as e:
        logger.error(f"Pterodactyl nests error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pterodactyl/eggs', methods=['GET'])
@role_required(['admin','operator'])
def get_pterodactyl_eggs():
    """Get all Pterodactyl eggs"""
    try:
        eggs = deployment_manager.get_pterodactyl_eggs()
        return jsonify({'success': True, 'eggs': eggs})
    except Exception as e:
        logger.error(f"Pterodactyl eggs error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pterodactyl/eggs/upload', methods=['POST'])
@role_required(['admin','operator'])
def upload_pterodactyl_egg():
    """Upload a new egg to Pterodactyl"""
    try:
        data = request.json
        nest_id = data.get('nest_id')
        egg_data = data.get('egg_data')

        if not nest_id or not egg_data:
            return jsonify({'success': False, 'error': 'Missing nest_id or egg_data'}), 400

        result = deployment_manager.upload_pterodactyl_egg(nest_id, egg_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Pterodactyl egg upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pterodactyl/nodes', methods=['GET'])
@role_required(['admin','operator'])
def get_pterodactyl_nodes():
    """Get Pterodactyl nodes"""
    try:
        nodes = deployment_manager.get_pterodactyl_nodes()
        return jsonify({'success': True, 'nodes': nodes})
    except Exception as e:
        logger.error(f"Pterodactyl nodes error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pterodactyl/nodes/<int:node_id>/allocations', methods=['GET'])
@role_required(['admin','operator'])
def get_pterodactyl_allocations(node_id):
    """Get available allocations for a node"""
    try:
        allocations = deployment_manager.get_pterodactyl_allocations(node_id)
        return jsonify({'success': True, 'allocations': allocations})
    except Exception as e:
        logger.error(f"Pterodactyl allocations error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# User Management Endpoints
@app.route('/api/users', methods=['GET'])
@role_required(['admin'])
def list_users():
    """List all users (admin only)"""
    try:
        users = auth_manager.list_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        logger.error(f"User list error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@role_required(['admin'])
def create_user():
    """Create new user (admin only)"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'viewer')
        email = data.get('email')

        result = auth_manager.create_user(username, password, role, email)
        return jsonify(result)
    except Exception as e:
        logger.error(f"User creation error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<username>', methods=['DELETE'])
@role_required(['admin'])
def delete_user(username):
    """Delete user (admin only)"""
    try:
        result = auth_manager.delete_user(username)
        return jsonify(result)
    except Exception as e:
        logger.error(f"User deletion error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<username>/role', methods=['PUT'])
@role_required(['admin'])
def update_user_role(username):
    """Update user role (admin only)"""
    try:
        data = request.json
        new_role = data.get('role')
        result = auth_manager.update_user_role(username, new_role)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Role update error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<username>/status', methods=['PUT'])
@role_required(['admin'])
def update_user_status(username):
    """Update user active status (admin only)"""
    try:
        data = request.json
        is_active = data.get('is_active')

        if is_active is None:
            return jsonify({'success': False, 'error': 'is_active field required'}), 400

        result = auth_manager.update_user_status(username, is_active)
        return jsonify(result)
    except Exception as e:
        logger.error(f"User status update error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<username>/password', methods=['PUT'])
@role_required(['admin'])
def reset_user_password(username):
    """Reset user password (admin only)"""
    try:
        data = request.json
        new_password = data.get('password')

        if not new_password:
            return jsonify({'success': False, 'error': 'Password required'}), 400

        if len(new_password) < 8:
            return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400

        result = auth_manager.reset_user_password(username, new_password)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/change-password', methods=['POST'])
@login_required
def change_password():
    """Change current user's password"""
    try:
        data = request.json
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        username = session.get('username')

        result = auth_manager.change_password(username, old_password, new_password)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper function to mask secrets
def mask_secrets(config):
    """Mask sensitive values in configuration"""
    if not isinstance(config, dict):
        return config

    masked = {}
    secret_keys = ['api_token', 'api_key', 'password', 'secret', 'pass']

    for key, value in config.items():
        if isinstance(value, dict):
            masked[key] = mask_secrets(value)
        elif any(secret in key.lower() for secret in secret_keys):
            # Show only last 4 characters
            if value and len(str(value)) > 4:
                masked[key] = '****' + str(value)[-4:]
            else:
                masked[key] = '****'
        else:
            masked[key] = value

    return masked

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs('/app/data', exist_ok=True)
    os.makedirs('/app/logs', exist_ok=True)
    os.makedirs('/app/templates/saved', exist_ok=True)

    # Run the application with SocketIO support
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
