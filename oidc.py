"""
OIDC Authentication for Wingman
Supports Keycloak and other OIDC-compliant identity providers
"""
import os
import json
import logging
from typing import Optional, Dict
from authlib.integrations.flask_client import OAuth
from flask import session, url_for, request

logger = logging.getLogger(__name__)

oauth = OAuth()


class OIDCManager:
    """Manages OIDC authentication flow"""

    def __init__(self, app=None):
        self.app = app
        self.providers = {}
        self.enabled = False

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize OIDC with Flask app"""
        self.app = app
        self.enabled = os.environ.get('ENABLE_OIDC', 'false').lower() == 'true'

        if not self.enabled:
            logger.info("OIDC authentication is disabled")
            return

        oauth.init_app(app)

        # Load provider from environment
        self._load_env_provider()

        # Load providers from database
        self._load_db_providers()

    def _load_env_provider(self):
        """Load OIDC provider from environment variables"""
        issuer = os.environ.get('OIDC_ISSUER')
        client_id = os.environ.get('OIDC_CLIENT_ID')
        client_secret = os.environ.get('OIDC_CLIENT_SECRET')

        if issuer and client_id and client_secret:
            try:
                self._register_provider(
                    name='default',
                    display_name=os.environ.get('OIDC_DISPLAY_NAME', 'SSO Login'),
                    issuer=issuer,
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=os.environ.get('OIDC_SCOPES', 'openid profile email'),
                    role_mapping=json.loads(os.environ.get('OIDC_ROLE_MAPPING', '{}')),
                    default_role=os.environ.get('OIDC_DEFAULT_ROLE', 'viewer')
                )
                logger.info("Loaded OIDC provider 'default' from environment")
            except Exception as e:
                logger.error(f"Failed to load OIDC provider from environment: {e}")

    def _load_db_providers(self):
        """Load additional OIDC providers from database"""
        try:
            from models import OIDCProvider
            providers = OIDCProvider.query.filter_by(is_enabled=True).all()

            for provider in providers:
                try:
                    role_mapping = json.loads(provider.role_mapping) if provider.role_mapping else {}
                    self._register_provider(
                        name=provider.name,
                        display_name=provider.display_name or provider.name,
                        issuer=provider.issuer,
                        client_id=provider.client_id,
                        client_secret=provider.client_secret,
                        scopes=provider.scopes or 'openid profile email',
                        role_mapping=role_mapping,
                        default_role=provider.default_role or 'viewer'
                    )
                    logger.info(f"Loaded OIDC provider '{provider.name}' from database")
                except Exception as e:
                    logger.error(f"Failed to load OIDC provider '{provider.name}': {e}")
        except Exception as e:
            logger.warning(f"Could not load OIDC providers from database: {e}")

    def _register_provider(self, name: str, display_name: str, issuer: str,
                           client_id: str, client_secret: str, scopes: str,
                           role_mapping: dict, default_role: str):
        """Register an OIDC provider with Authlib"""

        # Build metadata URL for auto-discovery
        metadata_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"

        oauth.register(
            name=name,
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url=metadata_url,
            client_kwargs={
                'scope': scopes
            }
        )

        self.providers[name] = {
            'display_name': display_name,
            'issuer': issuer,
            'role_mapping': role_mapping,
            'default_role': default_role,
            'scopes': scopes
        }

        logger.info(f"Registered OIDC provider: {name} ({issuer})")

    def get_providers(self) -> list:
        """Get list of available OIDC providers"""
        return [
            {
                'name': name,
                'display_name': config['display_name'],
                'type': 'oidc'
            }
            for name, config in self.providers.items()
        ]

    def get_authorization_url(self, provider_name: str = 'default') -> str:
        """Get the OIDC authorization URL"""
        if provider_name not in self.providers:
            raise ValueError(f"Unknown OIDC provider: {provider_name}")

        client = oauth.create_client(provider_name)
        redirect_uri = url_for('oidc_callback', provider=provider_name, _external=True)

        # Generate and store state for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        session['oidc_state'] = state
        session['oidc_provider'] = provider_name

        return client.create_authorization_url(redirect_uri, state=state)

    def handle_callback(self, provider_name: str = 'default') -> Optional[Dict]:
        """Handle OIDC callback and return user info"""
        if provider_name not in self.providers:
            logger.error(f"Unknown OIDC provider: {provider_name}")
            return None

        # Verify state for CSRF protection
        expected_state = session.pop('oidc_state', None)
        received_state = request.args.get('state')
        if not expected_state or expected_state != received_state:
            logger.error("OIDC state mismatch - possible CSRF attack")
            return None

        client = oauth.create_client(provider_name)

        try:
            # Exchange code for token
            token = client.authorize_access_token()

            # Get user info from ID token or userinfo endpoint
            userinfo = token.get('userinfo')
            if not userinfo:
                userinfo = client.parse_id_token(token)
            if not userinfo:
                userinfo = client.userinfo(token=token)

            if not userinfo:
                logger.error("Failed to get user info from OIDC provider")
                return None

            # Map role from claims
            role = self._map_role(provider_name, userinfo)

            return {
                'external_id': userinfo.get('sub'),
                'username': userinfo.get('preferred_username') or userinfo.get('email', '').split('@')[0],
                'email': userinfo.get('email'),
                'display_name': userinfo.get('name'),
                'role': role,
                'provider': provider_name,
                'raw_claims': userinfo
            }

        except Exception as e:
            logger.error(f"OIDC callback error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _map_role(self, provider_name: str, userinfo: dict) -> str:
        """Map OIDC claims/groups to local role"""
        provider_config = self.providers.get(provider_name, {})
        role_mapping = provider_config.get('role_mapping', {})
        default_role = provider_config.get('default_role', 'viewer')

        # Collect groups from various claim locations
        groups = set()

        # Standard groups claim
        if 'groups' in userinfo:
            if isinstance(userinfo['groups'], list):
                groups.update(userinfo['groups'])

        # Keycloak specific - realm_access.roles
        if 'realm_access' in userinfo and isinstance(userinfo['realm_access'], dict):
            if 'roles' in userinfo['realm_access']:
                groups.update(userinfo['realm_access']['roles'])

        # Keycloak specific - resource_access.{client}.roles
        if 'resource_access' in userinfo and isinstance(userinfo['resource_access'], dict):
            for client_data in userinfo['resource_access'].values():
                if isinstance(client_data, dict) and 'roles' in client_data:
                    groups.update(client_data['roles'])

        # Check role mapping (highest privilege first)
        for role in ['admin', 'operator', 'viewer']:
            mapped_groups = role_mapping.get(role, [])
            if isinstance(mapped_groups, list) and any(g in groups for g in mapped_groups):
                return role

        return default_role


# Global instance
oidc_manager = OIDCManager()
