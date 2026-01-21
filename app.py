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

# Initialize deployment manager
deployment_manager = DeploymentManager()

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        config = deployment_manager.get_config()
        return jsonify({'success': True, 'config': config})
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
