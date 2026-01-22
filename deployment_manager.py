#!/usr/bin/env python3
"""
Deployment Manager - Backend for Wingman Game Server Manager
Handles all deployment operations, API calls, and state management
"""

import os
import json
import logging
import requests
import threading
from datetime import datetime
from typing import Dict, List, Optional
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class DeploymentManager:
    """Manages game server deployments"""

    def __init__(self):
        self.data_dir = '/app/data'
        self.logs_dir = '/app/logs'
        self.templates_dir = '/app/templates/saved'
        self.deployments_file = os.path.join(self.data_dir, 'deployments.json')
        self.deployments = self._load_deployments()

        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)

        # Configuration from environment
        self.config = self._load_config_from_env()

    def _load_config_from_env(self) -> Dict:
        """Load configuration from environment variables"""
        return {
            'domain': os.environ.get('DOMAIN', 'yourdomain.com'),
            'cloudflare': {
                'api_token': os.environ.get('CF_API_TOKEN', ''),
                'zone_id': os.environ.get('CF_ZONE_ID', '')
            },
            'npm': {
                'api_url': os.environ.get('NPM_API_URL', ''),
                'email': os.environ.get('NPM_EMAIL', ''),
                'password': os.environ.get('NPM_PASSWORD', '')
            },
            'unifi': {
                'url': os.environ.get('UNIFI_URL', ''),
                'user': os.environ.get('UNIFI_USER', ''),
                'pass': os.environ.get('UNIFI_PASS', ''),
                'site': os.environ.get('UNIFI_SITE', 'default'),
                'is_udm': os.environ.get('UNIFI_IS_UDM', 'false').lower() == 'true'
            },
            'pterodactyl': {
                'url': os.environ.get('PTERO_URL', ''),
                'api_key': os.environ.get('PTERO_API_KEY', '')
            },
            'public_ip': os.environ.get('PUBLIC_IP', ''),
            'enable_auto_unifi': os.environ.get('ENABLE_AUTO_UNIFI', 'true').lower() == 'true',
            'enable_ssl_auto': os.environ.get('ENABLE_SSL_AUTO', 'true').lower() == 'true',
            'enable_monitoring': os.environ.get('ENABLE_MONITORING', 'false').lower() == 'true'
        }

    def _load_deployments(self) -> Dict:
        """Load deployments from file"""
        if os.path.exists(self.deployments_file):
            try:
                with open(self.deployments_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading deployments: {e}")
        return {}

    def _save_deployments(self):
        """Save deployments to file"""
        try:
            with open(self.deployments_file, 'w') as f:
                json.dump(self.deployments, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving deployments: {e}")

    def validate_config(self, config: Optional[Dict] = None) -> Dict:
        """Validate configuration"""
        cfg = config or self.config
        errors = []
        warnings = []

        logger.info(f"Validating configuration: {cfg.get('domain', 'NO_DOMAIN')}")

        # Domain is always required
        if not cfg.get('domain'):
            errors.append('Domain is not configured')

        # Validate Cloudflare if enabled
        cloudflare = cfg.get('cloudflare', {})
        if cloudflare.get('enabled'):
            if not cloudflare.get('api_token'):
                errors.append('Cloudflare is enabled but API token is not configured')
            if not cloudflare.get('zone_id'):
                errors.append('Cloudflare is enabled but Zone ID is not configured')
        elif not cloudflare.get('api_token'):
            warnings.append('Cloudflare API token not configured (feature disabled)')

        # Validate NPM if enabled
        npm = cfg.get('npm', {})
        if npm.get('enabled'):
            if not npm.get('api_url'):
                errors.append('Nginx Proxy Manager is enabled but API URL is not configured')
            if not npm.get('email'):
                errors.append('Nginx Proxy Manager is enabled but email is not configured')
            if not npm.get('password'):
                errors.append('Nginx Proxy Manager is enabled but password is not configured')
        elif not npm.get('api_url'):
            warnings.append('Nginx Proxy Manager not configured (feature disabled)')

        # Validate UniFi if enabled
        unifi = cfg.get('unifi', {})
        if unifi.get('enabled'):
            if not unifi.get('url'):
                errors.append('UniFi is enabled but Controller URL is not configured')
            if not unifi.get('user'):
                errors.append('UniFi is enabled but username is not configured')
            if not unifi.get('password'):
                errors.append('UniFi is enabled but password is not configured')
        elif not unifi.get('url'):
            warnings.append('UniFi Controller not configured (feature disabled)')

        # Validate Pterodactyl if enabled
        pterodactyl = cfg.get('pterodactyl', {})
        if pterodactyl.get('enabled'):
            if not pterodactyl.get('url'):
                errors.append('Pterodactyl is enabled but URL is not configured')
            if not pterodactyl.get('api_key'):
                errors.append('Pterodactyl is enabled but API key is not configured')
        elif not pterodactyl.get('url'):
            warnings.append('Pterodactyl not configured (feature disabled)')

        logger.info(f"Validation complete: {len(errors)} errors, {len(warnings)} warnings")

        return {
            'success': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def test_api_connectivity(self, config: Optional[Dict] = None) -> Dict:
        """Test connectivity to all configured APIs with detailed error reporting"""
        from errors import handle_api_error, CloudflareError, NPMError, UniFiError, PterodactylError

        cfg = config or self.config
        results = {
            'success': True,
            'tests': {},
            'errors': {},
            'details': {}
        }

        # Test Cloudflare
        if cfg.get('cloudflare', {}).get('api_token'):
            try:
                response = requests.get(
                    'https://api.cloudflare.com/client/v4/user/tokens/verify',
                    headers={'Authorization': f"Bearer {cfg['cloudflare']['api_token']}"},
                    timeout=10
                )
                if response.status_code == 200:
                    results['tests']['Cloudflare'] = True
                    results['details']['Cloudflare'] = 'API token verified successfully'
                else:
                    results['tests']['Cloudflare'] = False
                    error = CloudflareError(
                        'Cloudflare API token validation failed',
                        f'HTTP {response.status_code}: {response.text[:200]}',
                        response.status_code
                    )
                    results['errors']['Cloudflare'] = error.to_dict()
                    logger.error(f"Cloudflare test failed: {error.message}")
            except Exception as e:
                results['tests']['Cloudflare'] = False
                error = handle_api_error(e, 'Cloudflare')
                results['errors']['Cloudflare'] = error.to_dict()
                logger.error(f"Cloudflare test failed: {e}")
        else:
            results['tests']['Cloudflare'] = None
            results['details']['Cloudflare'] = 'Not configured'

        # Test NPM with authentication
        if cfg.get('npm', {}).get('api_url'):
            try:
                # Try to authenticate to NPM
                auth_response = requests.post(
                    f"{cfg['npm']['api_url']}/tokens",
                    json={'identity': cfg['npm']['email'], 'secret': cfg['npm']['password']},
                    timeout=10
                )
                if auth_response.status_code == 200:
                    token = auth_response.json().get('token')
                    # Verify token works
                    verify_response = requests.get(
                        f"{cfg['npm']['api_url']}/users/me",
                        headers={'Authorization': f"Bearer {token}"},
                        timeout=5
                    )
                    if verify_response.status_code == 200:
                        results['tests']['NPM'] = True
                        results['details']['NPM'] = 'Authentication successful'
                    else:
                        results['tests']['NPM'] = False
                        error = NPMError(
                            'NPM authentication succeeded but user verification failed',
                            f'HTTP {verify_response.status_code}: {verify_response.text[:200]}',
                            verify_response.status_code
                        )
                        results['errors']['NPM'] = error.to_dict()
                else:
                    results['tests']['NPM'] = False
                    error = NPMError(
                        'NPM authentication failed',
                        f'HTTP {auth_response.status_code}: {auth_response.text[:200]}',
                        auth_response.status_code
                    )
                    results['errors']['NPM'] = error.to_dict()
                    logger.error(f"NPM test failed: {error.message}")
            except Exception as e:
                results['tests']['NPM'] = False
                error = handle_api_error(e, 'NPM')
                results['errors']['NPM'] = error.to_dict()
                logger.error(f"NPM test failed: {e}")
        else:
            results['tests']['NPM'] = None
            results['details']['NPM'] = 'Not configured'

        # Test UniFi
        if cfg.get('unifi', {}).get('url'):
            try:
                verify_ssl = cfg.get('unifi', {}).get('verify_ssl', False)
                response = requests.get(cfg['unifi']['url'], verify=verify_ssl, timeout=5)
                results['tests']['UniFi'] = True
                results['details']['UniFi'] = 'Controller reachable'
            except Exception as e:
                results['tests']['UniFi'] = False
                error = handle_api_error(e, 'UniFi Controller')
                results['errors']['UniFi'] = error.to_dict()
                logger.error(f"UniFi test failed: {e}")
        else:
            results['tests']['UniFi'] = None
            results['details']['UniFi'] = 'Not configured'

        # Test Pterodactyl
        if cfg.get('pterodactyl', {}).get('url') and cfg.get('pterodactyl', {}).get('api_key'):
            try:
                verify_ssl = cfg.get('pterodactyl', {}).get('verify_ssl', True)
                response = requests.get(
                    f"{cfg['pterodactyl']['url']}/api/application/nodes",
                    headers={
                        'Authorization': f"Bearer {cfg['pterodactyl']['api_key']}",
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    timeout=10,
                    verify=verify_ssl
                )
                if response.status_code == 200:
                    results['tests']['Pterodactyl'] = True
                    node_count = len(response.json().get('data', []))
                    results['details']['Pterodactyl'] = f'Connected successfully ({node_count} nodes found)'
                else:
                    results['tests']['Pterodactyl'] = False
                    error = PterodactylError(
                        'Pterodactyl API request failed',
                        f'HTTP {response.status_code}: {response.text[:200]}',
                        response.status_code
                    )
                    results['errors']['Pterodactyl'] = error.to_dict()
                    logger.error(f"Pterodactyl test failed: {error.message}")
            except requests.exceptions.SSLError as e:
                results['tests']['Pterodactyl'] = False
                error = PterodactylError(
                    'Pterodactyl SSL certificate verification failed',
                    f'{str(e)}. Try setting PTERO_VERIFY_SSL=false in configuration',
                    'SSL_ERROR'
                )
                results['errors']['Pterodactyl'] = error.to_dict()
                logger.error(f"Pterodactyl SSL error: {e}")
            except Exception as e:
                results['tests']['Pterodactyl'] = False
                error = handle_api_error(e, 'Pterodactyl')
                results['errors']['Pterodactyl'] = error.to_dict()
                logger.error(f"Pterodactyl test failed: {e}")
        else:
            results['tests']['Pterodactyl'] = None
            results['details']['Pterodactyl'] = 'Not configured'

        # Overall success
        results['success'] = all(v in [True, None] for v in results['tests'].values())
        return results

    _SAFE_TEMPLATE_NAME = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

    def _template_path(self, name: str) -> Path:
        """Resolve a template path safely to prevent path traversal."""
        if not name or not self._SAFE_TEMPLATE_NAME.match(name):
            raise ValueError('Invalid template name (allowed: a-zA-Z0-9_- up to 64 chars)')

        base = Path(self.templates_dir).resolve()
        path = (base / f"{name}.json").resolve()
        if base not in path.parents and path != base:
            raise ValueError('Invalid template path')
        return path

    def list_templates(self) -> List[Dict]:
        """List available templates"""
        templates = []
        try:
            for filename in os.listdir(self.templates_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.templates_dir, filename)
                    with open(filepath, 'r') as f:
                        template = json.load(f)
                        templates.append(template)
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
        return templates

    def get_template(self, name: str) -> Optional[Dict]:
        """Get a specific template"""
        try:
            filepath = self._template_path(name)
            if filepath.exists():
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading template {name}: {e}")
        return None

    def save_template(self, template_data: Dict) -> Dict:
        """Save a deployment template"""
        try:
            name = template_data.get('name')
            if not name:
                return {'success': False, 'error': 'Template name is required'}

            filepath = self._template_path(name)
            with open(filepath, 'w') as f:
                json.dump(template_data, f, indent=2)

            return {'success': True, 'message': 'Template saved successfully'}
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return {'success': False, 'error': str(e)}

    def start_deployment(self, deployment_config: Dict) -> str:
        """Start a new deployment"""
        deployment_id = f"deploy_{int(time.time())}_{os.getpid()}"

        deployment = {
            'deployment_id': deployment_id,
            'subdomain': deployment_config.get('subdomain'),
            'server_ip': deployment_config.get('server_ip'),
            'game_port': deployment_config.get('game_port'),
            'game_type': deployment_config.get('game_type'),
            'additional_ports': deployment_config.get('additional_ports', []),
            'memory': deployment_config.get('memory', 4096),
            'disk': deployment_config.get('disk', 10240),
            'enable_ssl': deployment_config.get('enable_ssl', True),
            'enable_monitoring': deployment_config.get('enable_monitoring', False),
            'protocol': deployment_config.get('protocol', 'tcp_udp'),
            'domain': self.config['domain'],
            'created_at': datetime.now().isoformat(),
            'status': 'in_progress',
            'state': 'starting',
            'progress': 0,
            'steps': [],
            'cf_record_id': None,
            'unifi_rule_ids': [],
            'npm_proxy_id': None,
            'ptero_server_uuid': None,
            'logs': []
        }

        self.deployments[deployment_id] = deployment
        self._save_deployments()

        # Start deployment in background thread
        thread = threading.Thread(target=self._execute_deployment, args=(deployment_id,))
        thread.daemon = True
        thread.start()

        # Save template if requested
        if deployment_config.get('save_template') and deployment_config.get('template_name'):
            self.save_template({
                'name': deployment_config['template_name'],
                'game_type': deployment_config.get('game_type'),
                'game_port': deployment_config.get('game_port'),
                'memory': deployment_config.get('memory'),
                'disk': deployment_config.get('disk'),
                'additional_ports': deployment_config.get('additional_ports', []),
                'protocol': deployment_config.get('protocol', 'tcp_udp')
            })

        return deployment_id

    def _execute_deployment(self, deployment_id: str):
        """Execute deployment steps"""
        deployment = self.deployments[deployment_id]

        try:
            # Step 1: Cloudflare DNS
            self._update_deployment_step(deployment_id, 'Cloudflare DNS', 'active', 10)
            self._configure_cloudflare(deployment)
            self._update_deployment_step(deployment_id, 'Cloudflare DNS', 'completed', 25)

            # Step 2: UniFi Port Forwarding
            if self.config['enable_auto_unifi']:
                self._update_deployment_step(deployment_id, 'UniFi Port Forwarding', 'active', 30)
                self._configure_unifi(deployment)
                self._update_deployment_step(deployment_id, 'UniFi Port Forwarding', 'completed', 50)

            # Step 3: Nginx Proxy Manager
            self._update_deployment_step(deployment_id, 'Nginx Proxy Manager', 'active', 55)
            self._configure_npm(deployment)
            self._update_deployment_step(deployment_id, 'Nginx Proxy Manager', 'completed', 75)

            # Step 4: Pterodactyl (optional)
            if self.config['pterodactyl'].get('enabled') and deployment.get('pterodactyl_egg_id'):
                self._update_deployment_step(deployment_id, 'Pterodactyl Server', 'active', 80)
                self._add_log(deployment_id, "Creating Pterodactyl game server...")

                result = self.create_pterodactyl_server(deployment)

                if result['success']:
                    deployment['pterodactyl_server_id'] = result['server_id']
                    deployment['pterodactyl_server_uuid'] = result['server_uuid']
                    self._add_log(deployment_id, f"✓ Server created: {result['server_name']} (ID: {result['server_id']})")
                    self._update_deployment_step(deployment_id, 'Pterodactyl Server', 'completed', 100)
                else:
                    raise Exception(f"Pterodactyl server creation failed: {result['error']}")
            else:
                self._add_log(deployment_id, "Skipping Pterodactyl (not configured or no egg selected)")

            # Mark as completed
            deployment['status'] = 'completed'
            deployment['state'] = 'completed'
            deployment['progress'] = 100
            self._save_deployments()

        except Exception as e:
            logger.error(f"Deployment {deployment_id} failed: {e}")
            deployment['status'] = 'failed'
            deployment['state'] = 'failed'
            deployment['error'] = str(e)
            self._add_log(deployment_id, f"ERROR: {str(e)}")
            self._save_deployments()

    def _update_deployment_step(self, deployment_id: str, step_name: str, status: str, progress: int):
        """Update deployment step status and emit WebSocket event"""
        deployment = self.deployments[deployment_id]
        deployment['progress'] = progress

        # Update or add step
        step_found = False
        for step in deployment['steps']:
            if step['name'] == step_name:
                step['status'] = status
                step_found = True
                break

        if not step_found:
            deployment['steps'].append({'name': step_name, 'status': status})

        self._add_log(deployment_id, f"Step: {step_name} - {status}")
        self._save_deployments()

        # Emit WebSocket event for progress update
        try:
            from app import socketio
            socketio.emit('deployment_progress', {
                'deployment_id': deployment_id,
                'step_name': step_name,
                'status': status,
                'progress': progress,
                'steps': deployment['steps']
            })
        except Exception as e:
            logger.debug(f"Failed to emit progress WebSocket event: {e}")

    def _add_log(self, deployment_id: str, message: str):
        """Add log entry to deployment and emit WebSocket event"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.deployments[deployment_id]['logs'].append(log_entry)

        # Emit WebSocket event for real-time updates
        try:
            # Import here to avoid circular dependency
            from app import socketio
            socketio.emit('deployment_log', {
                'deployment_id': deployment_id,
                'message': message,
                'timestamp': timestamp,
                'log_entry': log_entry
            })
        except Exception as e:
            # Don't fail deployment if WebSocket emission fails
            logger.debug(f"Failed to emit WebSocket event: {e}")

    def _configure_cloudflare(self, deployment: Dict):
        """Configure Cloudflare DNS"""
        cf_config = self.config['cloudflare']
        if not cf_config['api_token'] or not cf_config['zone_id']:
            raise Exception("Cloudflare not configured")

        # Get public IP
        public_ip = self.config['public_ip']
        if not public_ip:
            response = requests.get('https://api.ipify.org', timeout=10)
            public_ip = response.text.strip()

        # Create DNS record
        response = requests.post(
            f"https://api.cloudflare.com/client/v4/zones/{cf_config['zone_id']}/dns_records",
            headers={
                'Authorization': f"Bearer {cf_config['api_token']}",
                'Content-Type': 'application/json'
            },
            json={
                'type': 'A',
                'name': deployment['subdomain'],
                'content': public_ip,
                'ttl': 1,
                'proxied': False
            },
            timeout=10
        )

        result = response.json()
        if result.get('success'):
            deployment['cf_record_id'] = result['result']['id']
            self._add_log(deployment['deployment_id'], f"Cloudflare DNS record created: {deployment['cf_record_id']}")
        else:
            raise Exception(f"Cloudflare API error: {result.get('errors')}")

    def _configure_unifi(self, deployment: Dict):
        """Configure UniFi port forwarding"""
        unifi_config = self.config['unifi']
        if not unifi_config['url']:
            self._add_log(deployment['deployment_id'], "UniFi not configured, skipping")
            return

        # This is a simplified implementation
        # Full implementation would include proper authentication and API calls
        self._add_log(deployment['deployment_id'], "UniFi port forwarding configuration (placeholder)")

    def _configure_npm(self, deployment: Dict):
        """Configure Nginx Proxy Manager"""
        npm_config = self.config['npm']
        if not npm_config['api_url']:
            raise Exception("NPM not configured")

        # This is a simplified implementation
        # Full implementation would include proper authentication and proxy creation
        self._add_log(deployment['deployment_id'], "NPM proxy configuration (placeholder)")

    def get_deployment_status(self, deployment_id: str) -> Optional[Dict]:
        """Get deployment status"""
        return self.deployments.get(deployment_id)

    def list_deployments(self) -> List[Dict]:
        """List all deployments"""
        return list(self.deployments.values())

    def rollback_deployment(self, deployment_id: str) -> Dict:
        """Rollback a deployment"""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            return {'success': False, 'error': 'Deployment not found'}

        try:
            # Rollback Cloudflare
            if deployment.get('cf_record_id'):
                cf_config = self.config['cloudflare']
                requests.delete(
                    f"https://api.cloudflare.com/client/v4/zones/{cf_config['zone_id']}/dns_records/{deployment['cf_record_id']}",
                    headers={'Authorization': f"Bearer {cf_config['api_token']}"},
                    timeout=10
                )

            # Mark as rolled back
            deployment['status'] = 'rolled_back'
            deployment['rolled_back_at'] = datetime.now().isoformat()
            self._save_deployments()

            return {'success': True, 'message': 'Deployment rolled back successfully'}
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {'success': False, 'error': str(e)}

    def get_deployment_logs(self, deployment_id: str) -> List[str]:
        """Get deployment logs"""
        deployment = self.deployments.get(deployment_id)
        if deployment:
            return deployment.get('logs', [])
        return []

    def get_monitoring_stats(self) -> Dict:
        """Get monitoring statistics"""
        total = len(self.deployments)
        active = sum(1 for d in self.deployments.values() if d['status'] == 'completed')
        failed = sum(1 for d in self.deployments.values() if d['status'] == 'failed')

        return {
            'total_deployments': total,
            'active_deployments': active,
            'failed_deployments': failed,
            'avg_deploy_time': '-'
        }

    def get_config(self) -> Dict:
        """Get current configuration"""
        config_file = os.path.join(self.data_dir, 'config.json')

        # Try to load from file first
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    saved_config = json.load(f)
                    # Merge with environment defaults
                    for key, value in self.config.items():
                        if key not in saved_config:
                            saved_config[key] = value
                    logger.info(f"Loaded configuration from file: {config_file}")
                    return saved_config
            except Exception as e:
                logger.error(f"Error loading config file: {e}")
                logger.exception(e)

        # Return environment-based config as fallback
        logger.info("Using environment-based configuration (no config file found)")
        return self.config.copy()

    def save_config(self, config: Dict) -> Dict:
        """Save configuration"""
        config_file = os.path.join(self.data_dir, 'config.json')

        try:
            logger.info(f"Saving configuration to {config_file}")
            logger.debug(f"Config data: {json.dumps(config, indent=2)}")

            # Add enabled flags if not present
            if 'cloudflare' in config and 'enabled' not in config['cloudflare']:
                config['cloudflare']['enabled'] = bool(config['cloudflare'].get('api_token'))
            if 'npm' in config and 'enabled' not in config['npm']:
                config['npm']['enabled'] = bool(config['npm'].get('api_url'))
            if 'unifi' in config and 'enabled' not in config['unifi']:
                config['unifi']['enabled'] = bool(config['unifi'].get('url'))
            if 'pterodactyl' in config and 'enabled' not in config['pterodactyl']:
                config['pterodactyl']['enabled'] = bool(config['pterodactyl'].get('url'))

            # Save to file
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

            # Update runtime config
            self.config = config

            logger.info("Configuration saved successfully")
            return {'success': True, 'message': 'Configuration saved successfully'}
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            logger.exception(e)
            return {'success': False, 'error': str(e)}

    def get_pterodactyl_nests(self) -> List[Dict]:
        """Get list of Pterodactyl nests"""
        config = self.get_config()
        ptero = config.get('pterodactyl', {})

        if not ptero.get('enabled') or not ptero.get('url') or not ptero.get('api_key'):
            logger.warning("Pterodactyl not configured or not enabled")
            return []

        try:
            url = f"{ptero['url'].rstrip('/')}/api/application/nests?include=eggs"
            headers = {
                'Authorization': f"Bearer {ptero['api_key']}",
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching Pterodactyl nests: {e}")
            return []

    def get_pterodactyl_eggs(self) -> List[Dict]:
        """Get all Pterodactyl eggs from all nests"""
        nests = self.get_pterodactyl_nests()
        all_eggs = []

        for nest in nests:
            nest_id = nest['attributes']['id']
            nest_name = nest['attributes']['name']

            # Get eggs from relationship data if available
            eggs_data = nest.get('relationships', {}).get('eggs', {}).get('data', [])

            for egg in eggs_data:
                egg_info = {
                    'id': egg['attributes']['id'],
                    'name': egg['attributes']['name'],
                    'description': egg['attributes'].get('description', ''),
                    'author': egg['attributes'].get('author', 'Unknown'),
                    'nest_id': nest_id,
                    'nest_name': nest_name
                }
                all_eggs.append(egg_info)

        return all_eggs

    def upload_pterodactyl_egg(self, nest_id: int, egg_data: Dict) -> Dict:
        """Upload a new egg to Pterodactyl"""
        config = self.get_config()
        ptero = config.get('pterodactyl', {})

        if not ptero.get('enabled') or not ptero.get('url') or not ptero.get('api_key'):
            return {'success': False, 'error': 'Pterodactyl not configured or not enabled'}

        try:
            url = f"{ptero['url'].rstrip('/')}/api/application/nests/{nest_id}/eggs"
            headers = {
                'Authorization': f"Bearer {ptero['api_key']}",
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }

            # Transform egg data to API format
            payload = {
                'name': egg_data.get('name', 'Imported Egg'),
                'description': egg_data.get('description', ''),
                'docker_image': egg_data.get('docker_image', egg_data.get('docker_images', {}).get('default', 'ubuntu:latest')),
                'startup': egg_data.get('startup', ''),
                'config': egg_data.get('config', {}),
                'environment': egg_data.get('variables', [])
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            logger.info(f"Successfully uploaded egg to nest {nest_id}")
            return {'success': True, 'message': 'Egg uploaded successfully', 'data': response.json()}
        except requests.exceptions.RequestException as e:
            error_msg = f"Error uploading egg: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"Error uploading egg: {error_detail}"
                except:
                    error_msg = f"Error uploading egg: {e.response.text}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            logger.error(f"Unexpected error uploading egg: {e}")
            return {'success': False, 'error': str(e)}

    def get_pterodactyl_nodes(self) -> List[Dict]:
        """Get list of Pterodactyl nodes"""
        config = self.get_config()
        ptero = config.get('pterodactyl', {})

        if not ptero.get('enabled') or not ptero.get('url') or not ptero.get('api_key'):
            logger.warning("Pterodactyl not configured or not enabled")
            return []

        try:
            url = f"{ptero['url'].rstrip('/')}/api/application/nodes"
            headers = {
                'Authorization': f"Bearer {ptero['api_key']}",
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            nodes = []
            for node in data.get('data', []):
                nodes.append({
                    'id': node['attributes']['id'],
                    'name': node['attributes']['name'],
                    'fqdn': node['attributes']['fqdn'],
                    'memory': node['attributes']['memory'],
                    'disk': node['attributes']['disk'],
                    'allocated_memory': node['attributes']['allocated_resources']['memory'],
                    'allocated_disk': node['attributes']['allocated_resources']['disk']
                })
            return nodes
        except Exception as e:
            logger.error(f"Error fetching Pterodactyl nodes: {e}")
            return []

    def get_pterodactyl_allocations(self, node_id: int) -> List[Dict]:
        """Get available port allocations for a node"""
        config = self.get_config()
        ptero = config.get('pterodactyl', {})

        if not ptero.get('enabled') or not ptero.get('url') or not ptero.get('api_key'):
            logger.warning("Pterodactyl not configured or not enabled")
            return []

        try:
            url = f"{ptero['url'].rstrip('/')}/api/application/nodes/{node_id}/allocations"
            headers = {
                'Authorization': f"Bearer {ptero['api_key']}",
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            allocations = []
            for alloc in data.get('data', []):
                # Only include unassigned allocations
                if not alloc['attributes']['assigned']:
                    allocations.append({
                        'id': alloc['attributes']['id'],
                        'ip': alloc['attributes']['ip'],
                        'port': alloc['attributes']['port'],
                        'alias': alloc['attributes'].get('alias', alloc['attributes']['ip'])
                    })
            return allocations
        except Exception as e:
            logger.error(f"Error fetching Pterodactyl allocations: {e}")
            return []

    def create_pterodactyl_server(self, deployment: Dict) -> Dict:
        """Create a server in Pterodactyl"""
        config = self.get_config()
        ptero = config.get('pterodactyl', {})

        if not ptero.get('enabled') or not ptero.get('url') or not ptero.get('api_key'):
            return {'success': False, 'error': 'Pterodactyl not configured or not enabled'}

        try:
            # Get deployment parameters
            nest_id = deployment.get('pterodactyl_nest_id')
            egg_id = deployment.get('pterodactyl_egg_id')
            node_id = deployment.get('pterodactyl_node_id')
            allocation_id = deployment.get('pterodactyl_allocation_id')

            if not all([nest_id, egg_id, node_id, allocation_id]):
                return {'success': False, 'error': 'Missing required Pterodactyl parameters (nest, egg, node, or allocation)'}

            # Prepare server creation payload
            server_name = f"{deployment.get('subdomain', 'server')}-{deployment.get('game_type', 'game')}"

            payload = {
                'name': server_name,
                'user': ptero.get('default_user_id', 1),  # TODO: Make this configurable
                'egg': egg_id,
                'docker_image': 'ghcr.io/pterodactyl/yolks:java_17',  # Will be overridden by egg default
                'startup': '',  # Will use egg default
                'environment': {},  # Can be customized per deployment
                'limits': {
                    'memory': deployment.get('memory_mb', 2048),
                    'swap': 0,
                    'disk': deployment.get('disk_mb', 10240),
                    'io': 500,
                    'cpu': deployment.get('cpu_limit', 100)
                },
                'feature_limits': {
                    'databases': ptero.get('default_databases', 1),
                    'backups': ptero.get('default_backups', 2),
                    'allocations': 1
                },
                'allocation': {
                    'default': allocation_id
                }
            }

            url = f"{ptero['url'].rstrip('/')}/api/application/servers"
            headers = {
                'Authorization': f"Bearer {ptero['api_key']}",
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            server_data = response.json()
            server_id = server_data['attributes']['id']
            server_uuid = server_data['attributes']['uuid']

            logger.info(f"Successfully created Pterodactyl server {server_id} ({server_name})")

            return {
                'success': True,
                'message': f'Server {server_name} created successfully',
                'server_id': server_id,
                'server_uuid': server_uuid,
                'server_name': server_name
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"Error creating Pterodactyl server: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"Pterodactyl API error: {error_detail.get('errors', [{}])[0].get('detail', str(error_detail))}"
                except:
                    error_msg = f"Pterodactyl API error: {e.response.text[:200]}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            logger.error(f"Unexpected error creating Pterodactyl server: {e}")
            return {'success': False, 'error': str(e)}
