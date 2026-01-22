"""
Custom exceptions and error handling for Wingman
Provides structured error responses with troubleshooting guidance
"""

class WingmanError(Exception):
    """Base exception for all Wingman errors"""
    def __init__(self, message, details=None, service=None, code=None):
        self.message = message
        self.details = details or str(message)
        self.service = service
        self.code = code
        self.troubleshooting = []
        self.docs_url = None
        super().__init__(self.message)

    def to_dict(self):
        """Convert to structured error response"""
        return {
            'message': self.message,
            'details': self.details,
            'service': self.service,
            'code': self.code,
            'troubleshooting': self.troubleshooting,
            'docs_url': self.docs_url
        }


class CloudflareError(WingmanError):
    """Cloudflare API errors"""
    def __init__(self, message, details=None, status_code=None):
        super().__init__(message, details, 'Cloudflare', f'ERR_CF_{status_code or "UNKNOWN"}')
        self.troubleshooting = [
            'Verify your Cloudflare API token is correct',
            'Ensure the token has "Zone.DNS" permissions',
            'Check that the Zone ID matches your domain',
            'Verify the domain is active in Cloudflare'
        ]
        self.docs_url = 'https://github.com/treestandk/wingman/blob/main/docs/TROUBLESHOOTING.md#cloudflare'


class NPMError(WingmanError):
    """Nginx Proxy Manager API errors"""
    def __init__(self, message, details=None, status_code=None):
        super().__init__(message, details, 'Nginx Proxy Manager', f'ERR_NPM_{status_code or "UNKNOWN"}')
        self.troubleshooting = [
            'Check NPM is running and accessible at the configured URL',
            'Verify NPM API URL format: http://npm-ip:81/api',
            'Ensure email and password are correct',
            'Check network connectivity between containers/hosts',
            'Verify NPM version is compatible (tested with 2.9+)'
        ]
        self.docs_url = 'https://github.com/treestandk/wingman/blob/main/docs/TROUBLESHOOTING.md#nginx-proxy-manager'


class UniFiError(WingmanError):
    """UniFi Controller API errors"""
    def __init__(self, message, details=None):
        super().__init__(message, details, 'UniFi Controller', 'ERR_UNIFI')
        self.troubleshooting = [
            'Verify UniFi Controller URL is correct (include https://)',
            'Check username and password are correct',
            'Ensure the user has admin permissions',
            'Verify site name matches (default: "default")',
            'If using UDM, set UNIFI_IS_UDM=true',
            'For self-signed certs, consider setting UNIFI_VERIFY_SSL=false'
        ]
        self.docs_url = 'https://github.com/treestandk/wingman/blob/main/docs/TROUBLESHOOTING.md#unifi'


class PterodactylError(WingmanError):
    """Pterodactyl Panel API errors"""
    def __init__(self, message, details=None, status_code=None):
        super().__init__(message, details, 'Pterodactyl', f'ERR_PTERO_{status_code or "UNKNOWN"}')
        self.troubleshooting = [
            'Verify Pterodactyl URL is correct (include https://)',
            'Ensure you are using an APPLICATION API key (not Client API key)',
            'Check API key has required permissions (nodes, eggs, servers)',
            'Verify Pterodactyl panel is accessible',
            'Check API version compatibility (tested with v1.x)',
            'For SSL issues, verify certificate or set PTERO_VERIFY_SSL=false'
        ]
        self.docs_url = 'https://github.com/treestandk/wingman/blob/main/docs/TROUBLESHOOTING.md#pterodactyl'


class ConfigurationError(WingmanError):
    """Configuration validation errors"""
    def __init__(self, message, details=None, field=None):
        super().__init__(message, details, 'Configuration', f'ERR_CONFIG_{field or "INVALID"}')
        self.troubleshooting = [
            'Review all configuration settings in the Settings tab',
            'Ensure all required fields are filled',
            'Verify URLs include protocol (http:// or https://)',
            'Check environment variables are set correctly',
            'Use Test Connectivity to validate each service'
        ]
        self.docs_url = 'https://github.com/treestandk/wingman/blob/main/docs/QUICKSTART.md#configuration'


class DeploymentError(WingmanError):
    """Deployment operation errors"""
    def __init__(self, message, details=None, step=None):
        super().__init__(message, details, 'Deployment', f'ERR_DEPLOY_{step or "FAILED"}')
        self.troubleshooting = [
            'Check deployment logs for detailed error information',
            'Verify all API services are configured and connected',
            'Ensure resources (ports, memory, disk) are available',
            'Review the deployment configuration for errors',
            'Try rolling back and redeploying with corrected settings'
        ]
        self.docs_url = 'https://github.com/treestandk/wingman/blob/main/docs/TROUBLESHOOTING.md#deployments'


class AuthenticationError(WingmanError):
    """Authentication and authorization errors"""
    def __init__(self, message, details=None):
        super().__init__(message, details, 'Authentication', 'ERR_AUTH_FAILED')
        self.troubleshooting = [
            'Verify username and password are correct',
            'Check if account is active and not locked',
            'Clear browser cookies and try again',
            'Contact administrator for password reset if needed'
        ]
        self.docs_url = 'https://github.com/treestandk/wingman/blob/main/docs/AUTHENTICATION.md#troubleshooting'


def handle_api_error(exception, service='Unknown'):
    """
    Convert generic exceptions to structured WingmanError

    Args:
        exception: The caught exception
        service: The service that raised the error

    Returns:
        WingmanError: Structured error with troubleshooting
    """
    import requests

    if isinstance(exception, requests.exceptions.SSLError):
        return WingmanError(
            f'SSL certificate verification failed for {service}',
            str(exception),
            service,
            'ERR_SSL_VERIFICATION'
        )
    elif isinstance(exception, requests.exceptions.ConnectionError):
        error = WingmanError(
            f'Cannot connect to {service}',
            str(exception),
            service,
            'ERR_CONNECTION'
        )
        error.troubleshooting = [
            f'Verify {service} is running and accessible',
            'Check URL/hostname is correct',
            'Verify network connectivity (firewall, DNS)',
            'Ensure port is not blocked',
            'Check container network configuration if using Docker'
        ]
        return error
    elif isinstance(exception, requests.exceptions.Timeout):
        error = WingmanError(
            f'{service} request timed out',
            str(exception),
            service,
            'ERR_TIMEOUT'
        )
        error.troubleshooting = [
            f'Check if {service} is responding slowly',
            'Verify network latency is acceptable',
            'Increase timeout value if needed',
            f'Check {service} server resources (CPU, memory)'
        ]
        return error
    elif isinstance(exception, requests.exceptions.RequestException):
        return WingmanError(
            f'{service} API request failed',
            str(exception),
            service,
            'ERR_REQUEST'
        )
    else:
        return WingmanError(
            f'Unexpected error with {service}',
            str(exception),
            service,
            'ERR_UNKNOWN'
        )
