#!/usr/bin/env python3
"""
Migration script to convert JSON-based user storage to SQLite
Run this once when upgrading Wingman to use the database backend.

Usage:
    python migrate_to_sqlite.py
"""
import os
import sys
import json
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_users(db, User, json_file: str = '/app/data/users.json'):
    """Migrate users from JSON file to SQLite"""
    # Also check local data directory for dev environments
    if not os.path.exists(json_file):
        json_file = 'data/users.json'
    if not os.path.exists(json_file):
        logger.info("No users.json file found, skipping user migration")
        return 0

    logger.info(f"Found users file at {json_file}")

    with open(json_file, 'r') as f:
        users_data = json.load(f)

    migrated = 0
    for username, data in users_data.items():
        # Check if user already exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            logger.info(f"User {username} already exists, skipping")
            continue

        # Parse created_at date
        created_at = None
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except (ValueError, TypeError):
                created_at = datetime.utcnow()

        # Parse last_login date
        last_login = None
        if data.get('last_login'):
            try:
                last_login = datetime.fromisoformat(data['last_login'])
            except (ValueError, TypeError):
                pass

        user = User(
            username=data.get('username', username),
            password_hash=data.get('password_hash'),
            email=data.get('email'),
            role=data.get('role', 'viewer'),
            is_active=data.get('is_active', True),
            auth_provider='local',
            created_at=created_at or datetime.utcnow(),
            last_login=last_login
        )
        db.session.add(user)
        migrated += 1
        logger.info(f"Migrated user: {username} (role: {user.role})")

    db.session.commit()

    # Backup old file
    if migrated > 0:
        backup_file = json_file + '.migrated'
        os.rename(json_file, backup_file)
        logger.info(f"Backed up old users file to {backup_file}")

    return migrated


def migrate_audit_logs(db, AuditLog, log_file: str = '/app/data/audit.log'):
    """Migrate audit logs from text file to SQLite"""
    # Also check local data directory for dev environments
    if not os.path.exists(log_file):
        log_file = 'data/audit.log'
    if not os.path.exists(log_file):
        logger.info("No audit.log file found, skipping audit migration")
        return 0

    logger.info(f"Found audit log at {log_file}")

    migrated = 0
    with open(log_file, 'r') as f:
        for line in f:
            try:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(' | ')
                if len(parts) >= 4:
                    timestamp = datetime.fromisoformat(parts[0])
                    action = parts[1]
                    username = parts[2]
                    ip_address = parts[3]
                    details = parts[4] if len(parts) > 4 else None

                    log_entry = AuditLog(
                        timestamp=timestamp,
                        action=action,
                        username=username,
                        ip_address=ip_address,
                        details=details
                    )
                    db.session.add(log_entry)
                    migrated += 1
            except Exception as e:
                logger.warning(f"Failed to migrate log line: {e}")

    db.session.commit()

    if migrated > 0:
        backup_file = log_file + '.migrated'
        os.rename(log_file, backup_file)
        logger.info(f"Backed up old audit log to {backup_file}")

    return migrated


def run_migration():
    """Run full migration"""
    # Set up minimal Flask app for database context
    from flask import Flask
    from models import db, User, AuditLog

    app = Flask(__name__)

    # Database configuration
    db_path = os.environ.get('DATABASE_URL', 'sqlite:///data/wingman.db')
    if db_path.startswith('sqlite:///') and not db_path.startswith('sqlite:////'):
        # Relative path - ensure directory exists
        db_file = db_path.replace('sqlite:///', '')
        os.makedirs(os.path.dirname(db_file) or '.', exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        # Create tables
        db.create_all()
        logger.info("Database tables created")

        # Migrate data
        users_count = migrate_users(db, User)
        logger.info(f"Migrated {users_count} users")

        logs_count = migrate_audit_logs(db, AuditLog)
        logger.info(f"Migrated {logs_count} audit log entries")

        # Verify migration
        total_users = User.query.count()
        total_logs = AuditLog.query.count()
        logger.info(f"Database now contains {total_users} users and {total_logs} audit entries")

        logger.info("Migration completed successfully!")


if __name__ == '__main__':
    run_migration()
