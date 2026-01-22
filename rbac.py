"""
Role-Based Access Control (RBAC) for Wingman
Defines permissions for different user roles
"""

# Define permissions for each role
PERMISSIONS = {
    'admin': {
        # Configuration
        'config.view': True,
        'config.edit': True,
        'config.test': True,

        # Deployments
        'deploy.create': True,
        'deploy.view': True,
        'deploy.rollback': True,
        'deploy.delete': True,
        'deploy.logs': True,

        # Templates
        'template.create': True,
        'template.view': True,
        'template.edit': True,
        'template.delete': True,

        # Pterodactyl
        'pterodactyl.view': True,
        'pterodactyl.manage': True,

        # User Management
        'users.view': True,
        'users.create': True,
        'users.edit': True,
        'users.delete': True,

        # Monitoring
        'monitoring.view': True,

        # System
        'system.settings': True,
    },
    'operator': {
        # Configuration
        'config.view': True,
        'config.edit': False,
        'config.test': True,

        # Deployments
        'deploy.create': True,
        'deploy.view': True,
        'deploy.rollback': True,
        'deploy.delete': False,
        'deploy.logs': True,

        # Templates
        'template.create': True,
        'template.view': True,
        'template.edit': True,
        'template.delete': True,

        # Pterodactyl
        'pterodactyl.view': True,
        'pterodactyl.manage': False,

        # User Management
        'users.view': False,
        'users.create': False,
        'users.edit': False,
        'users.delete': False,

        # Monitoring
        'monitoring.view': True,

        # System
        'system.settings': False,
    },
    'viewer': {
        # Configuration
        'config.view': False,
        'config.edit': False,
        'config.test': False,

        # Deployments
        'deploy.create': False,
        'deploy.view': True,
        'deploy.rollback': False,
        'deploy.delete': False,
        'deploy.logs': True,

        # Templates
        'template.create': False,
        'template.view': True,
        'template.edit': False,
        'template.delete': False,

        # Pterodactyl
        'pterodactyl.view': True,
        'pterodactyl.manage': False,

        # User Management
        'users.view': False,
        'users.create': False,
        'users.edit': False,
        'users.delete': False,

        # Monitoring
        'monitoring.view': True,

        # System
        'system.settings': False,
    }
}


def has_permission(role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission

    Args:
        role: User role (admin, operator, viewer)
        permission: Permission string (e.g., 'deploy.create')

    Returns:
        bool: True if role has permission, False otherwise
    """
    if role not in PERMISSIONS:
        return False

    return PERMISSIONS[role].get(permission, False)


def get_role_permissions(role: str) -> dict:
    """
    Get all permissions for a role

    Args:
        role: User role

    Returns:
        dict: All permissions for the role
    """
    return PERMISSIONS.get(role, {})


def get_allowed_actions(role: str, resource: str) -> list:
    """
    Get all allowed actions for a role on a specific resource

    Args:
        role: User role
        resource: Resource name (config, deploy, template, etc.)

    Returns:
        list: List of allowed actions
    """
    if role not in PERMISSIONS:
        return []

    prefix = f"{resource}."
    return [
        action.replace(prefix, '')
        for action, allowed in PERMISSIONS[role].items()
        if action.startswith(prefix) and allowed
    ]


# Permission descriptions for UI
PERMISSION_DESCRIPTIONS = {
    'config.view': 'View system configuration',
    'config.edit': 'Modify system configuration',
    'config.test': 'Test API connectivity',
    'deploy.create': 'Create new deployments',
    'deploy.view': 'View deployment status and history',
    'deploy.rollback': 'Rollback deployments',
    'deploy.delete': 'Delete deployments',
    'deploy.logs': 'View deployment logs',
    'template.create': 'Create deployment templates',
    'template.view': 'View deployment templates',
    'template.edit': 'Edit deployment templates',
    'template.delete': 'Delete deployment templates',
    'pterodactyl.view': 'View Pterodactyl nests and eggs',
    'pterodactyl.manage': 'Manage Pterodactyl resources',
    'users.view': 'View user accounts',
    'users.create': 'Create new users',
    'users.edit': 'Edit user accounts and roles',
    'users.delete': 'Delete user accounts',
    'monitoring.view': 'View monitoring statistics',
    'system.settings': 'Access system settings',
}


# Role descriptions for UI
ROLE_DESCRIPTIONS = {
    'admin': 'Full system access including user management and configuration',
    'operator': 'Can create and manage deployments but cannot modify system settings',
    'viewer': 'Read-only access to view deployments and logs',
}
