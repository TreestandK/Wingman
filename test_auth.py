#!/usr/bin/env python3
"""
Test script to verify authentication system works
Run this to debug auth issues
"""

import os
import sys

print("=" * 60)
print("Wingman Authentication Test")
print("=" * 60)
print()

# Check environment
print("Environment Variables:")
print(f"  ENABLE_AUTH: {os.environ.get('ENABLE_AUTH', 'not set')}")
print(f"  FLASK_SECRET_KEY: {os.environ.get('FLASK_SECRET_KEY', 'using default')[:20]}...")
print()

# Check directories
print("Directory Check:")
for directory in ['/app/data', '/app/logs', '/app/templates/saved']:
    exists = os.path.exists(directory)
    writable = os.access(directory, os.W_OK) if exists else False
    print(f"  {directory}: {'✓ exists' if exists else '✗ missing'}, {'✓ writable' if writable else '✗ not writable'}")
print()

# Try to import auth
print("Import Test:")
try:
    from auth import AuthManager
    print("  ✓ auth.py imported successfully")
except Exception as e:
    print(f"  ✗ Failed to import auth: {e}")
    sys.exit(1)

# Try to initialize AuthManager
print("\nAuthManager Initialization:")
try:
    auth_manager = AuthManager()
    print(f"  ✓ AuthManager initialized")
    print(f"  Auth enabled: {auth_manager.auth_enabled}")
    print(f"  Users loaded: {len(auth_manager.users)}")

    if auth_manager.users:
        print("\n  Users:")
        for username, user in auth_manager.users.items():
            print(f"    - {username} (role: {user.role}, active: {user.is_active})")
    else:
        print("  No users found")

        if auth_manager.auth_enabled:
            print("\n  ⚠️  WARNING: Auth is enabled but no users exist!")
            print("  The app should have created a default admin user.")
            print("  Check /app/logs/wingman.log for errors.")

except Exception as e:
    print(f"  ✗ Failed to initialize AuthManager: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ Authentication system test completed")
print("=" * 60)
