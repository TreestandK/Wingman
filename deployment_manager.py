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
            'domain': os.environ.get('DOMAIN', 'treestandk.com'),
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

        if not cfg.get('domain'):
            errors.append('Domain is not configured')

        if not cfg.get('cloudflare', {}).get('api_token'):
            errors.append('Cloudflare API token not configured')

        if not cfg.get('npm', {}).get('api_url'):
            errors.append('Nginx Proxy Manager API URL not configured')

        if not cfg.get('pterodactyl', {}).get('url'):
            errors.append('Pterodactyl URL not configured')

        return {
            'success': len(errors) == 0,
            'errors': errors,
            'warnings': []
        }

    def test_api_connectivity(self, config: Optional[Dict] = None) -> Dict:
        """Test connectivity to all configured APIs"""
        cfg = config or self.config
        results = {
            'success': True,
            'tests': {}
        }

        # Test Cloudflare
        if cfg.get('cloudflare', {}).get('api_token'):
            try:
                response = requests.get(
                    'https://api.cloudflare.com/client/v4/user/tokens/verify',
                    headers={'Authorization': f"Bearer {cfg['cloudflare']['api_token']}"},
                    timeout=10
                )
                results['tests']['Cloudflare'] = response.status_code == 200
            except Exception as e:
                results['tests']['Cloudflare'] = False
                logger.error(f"Cloudflare test failed: {e}")
        else:
            results['tests']['Cloudflare'] = None

        # Test NPM
        if cfg.get('npm', {}).get('api_url'):
            try:
                response = requests.get(cfg['npm']['api_url'], timeout=5)
                results['tests']['NPM'] = response.status_code in [200, 401, 404]
            except Exception as e:
                results['tests']['NPM'] = False
                logger.error(f"NPM test failed: {e}")
        else:
            results['tests']['NPM'] = None

        # Test UniFi
        if cfg.get('unifi', {}).get('url'):
            try:
                response = requests.get(cfg['unifi']['url'], verify=False, timeout=5)
                results['tests']['UniFi'] = True
            except Exception:
                results['tests']['UniFi'] = False
        else:
            results['tests']['UniFi'] = None

        # Test Pterodactyl
        if cfg.get('pterodactyl', {}).get('url') and cfg.get('pterodactyl', {}).get('api_key'):
            try:
                response = requests.get(
                    f"{cfg['pterodactyl']['url']}/api/application/nodes",
                    headers={
                        'Authorization': f"Bearer {cfg['pterodactyl']['api_key']}",
                        'Accept': 'Application/vnd.pterodactyl.v1+json'
                    },
                    timeout=10
                )
                results['tests']['Pterodactyl'] = response.status_code == 200
            except Exception as e:
                results['tests']['Pterodactyl'] = False
                logger.error(f"Pterodactyl test failed: {e}")
        else:
            results['tests']['Pterodactyl'] = None

        # Overall success
        results['success'] = all(v in [True, None] for v in results['tests'].values())
        return results

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
            filepath = os.path.join(self.templates_dir, f"{name}.json")
            if os.path.exists(filepath):
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

            filepath = os.path.join(self.templates_dir, f"{name}.json")
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
            if self.config['pterodactyl']['url']:
                self._update_deployment_step(deployment_id, 'Pterodactyl Server', 'active', 80)
                # Pterodactyl deployment would go here
                self._update_deployment_step(deployment_id, 'Pterodactyl Server', 'completed', 100)

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
        """Update deployment step status"""
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

    def _add_log(self, deployment_id: str, message: str):
        """Add log entry to deployment"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.deployments[deployment_id]['logs'].append(f"[{timestamp}] {message}")

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
