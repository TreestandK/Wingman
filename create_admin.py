#!/usr/bin/env python3
"""
CLI tool to create the first admin user for Wingman
Run this before enabling authentication
"""

import os
import sys
import getpass
from auth import AuthManager

def main():
    print("=" * 60)
    print("Wingman Admin User Creation Tool")
    print("=" * 60)
    print()

    # Initialize auth manager
    auth_manager = AuthManager()

    # Check if any admin users exist
    existing_admins = [u for u in auth_manager.users.values() if u.role == 'admin']

    if existing_admins:
        print(f"⚠️  Warning: {len(existing_admins)} admin user(s) already exist:")
        for admin in existing_admins:
            print(f"   - {admin.username}")
        print()
        response = input("Do you want to create another admin user? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return

    print("Creating new admin user...")
    print()

    # Get username
    while True:
        username = input("Enter username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            continue
        if username in auth_manager.users:
            print(f"❌ User '{username}' already exists")
            continue
        break

    # Get email (optional)
    email = input("Enter email (optional): ").strip() or None

    # Get password
    while True:
        password = getpass.getpass("Enter password: ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters")
            continue

        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("❌ Passwords do not match")
            continue
        break

    # Create user
    result = auth_manager.create_user(username, password, 'admin', email)

    if result['success']:
        print()
        print("=" * 60)
        print("✅ Admin user created successfully!")
        print("=" * 60)
        print(f"Username: {username}")
        print(f"Role: admin")
        if email:
            print(f"Email: {email}")
        print()
        print("To enable authentication, set environment variable:")
        print("  ENABLE_AUTH=true")
        print()
        print("Then restart the Wingman application.")
        print()
        print("You can now log in at: http://your-server:5000/login")
    else:
        print()
        print(f"❌ Error creating user: {result.get('error')}")
        sys.exit(1)

if __name__ == '__main__':
    main()
