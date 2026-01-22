#!/usr/bin/env python3
"""
Wingman Game Server Manager - Web Interface
Flask application for managing game server deployments
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import json
import logging
from datetime import datetime
from deployment_manager import DeploymentManager
from auth import AuthManager, login_required, role_required
from errors import WingmanError, handle_api_error

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/wingman.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize managers
deployment_manager = DeploymentManager()
auth_manager = AuthManager()

# Add cache-control headers to prevent aggressive browser caching
@app.after_request
def add_header(response):
    """Add headers to prevent caching of HTML pages (fixes Firefox caching issues)"""
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

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
def api_login():
    """Authenticate user"""
    try:
        if not auth_manager.auth_enabled:
            return jsonify({'success': False, 'error': 'Authentication not enabled'}), 400

        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400

        user = auth_manager.authenticate(username, password)
        if user:
            session['username'] = user.username
            session['role'] = user.role
            logger.info(f"User {username} logged in successfully")
            return jsonify({
                'success': True,
                'user': user.to_dict()
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

@app.route('/api/auth/debug', methods=['GET'])
def auth_debug():
    """Debug endpoint to troubleshoot auth issues"""
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
def test_connectivity():
    """Test API connectivity"""
    try:
        config = request.json
        test_results = deployment_manager.test_api_connectivity(config)
        return jsonify(test_results)
    except Exception as e:
        logger.error(f"Connectivity test error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/templates', methods=['GET'])
def list_templates():
    """List available deployment templates"""
    try:
        templates = deployment_manager.list_templates()
        return jsonify({'success': True, 'templates': templates})
    except Exception as e:
        logger.error(f"Template list error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/templates/<name>', methods=['GET'])
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
def list_deployments():
    """List all deployments"""
    try:
        deployments = deployment_manager.list_deployments()
        return jsonify({'success': True, 'deployments': deployments})
    except Exception as e:
        logger.error(f"Deployment list error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/deploy/<deployment_id>/rollback', methods=['POST'])
def rollback_deployment(deployment_id):
    """Rollback a deployment"""
    try:
        result = deployment_manager.rollback_deployment(deployment_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Rollback error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs/<deployment_id>', methods=['GET'])
def get_deployment_logs(deployment_id):
    """Get deployment logs"""
    try:
        logs = deployment_manager.get_deployment_logs(deployment_id)
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        logger.error(f"Log retrieval error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/monitoring/stats', methods=['GET'])
def get_monitoring_stats():
    """Get monitoring statistics"""
    try:
        stats = deployment_manager.get_monitoring_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Stats retrieval error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pterodactyl/nests', methods=['GET'])
def get_pterodactyl_nests():
    """Get Pterodactyl nests"""
    try:
        nests = deployment_manager.get_pterodactyl_nests()
        return jsonify({'success': True, 'nests': nests})
    except Exception as e:
        logger.error(f"Pterodactyl nests error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pterodactyl/eggs', methods=['GET'])
def get_pterodactyl_eggs():
    """Get all Pterodactyl eggs"""
    try:
        eggs = deployment_manager.get_pterodactyl_eggs()
        return jsonify({'success': True, 'eggs': eggs})
    except Exception as e:
        logger.error(f"Pterodactyl eggs error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pterodactyl/eggs/upload', methods=['POST'])
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
def get_pterodactyl_nodes():
    """Get Pterodactyl nodes"""
    try:
        nodes = deployment_manager.get_pterodactyl_nodes()
        return jsonify({'success': True, 'nodes': nodes})
    except Exception as e:
        logger.error(f"Pterodactyl nodes error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pterodactyl/nodes/<int:node_id>/allocations', methods=['GET'])
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

    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=False)
