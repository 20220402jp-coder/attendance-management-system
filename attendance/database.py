"""数据库版本升级。"""

import sqlite3

from config import DATABASE_PATH


LATEST_SCHEMA_VERSION = 2


def _columns(connection, table):
    return {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}


def run_migrations():
    """只增加缺失结构，不删除用户数据。"""
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            'CREATE TABLE IF NOT EXISTS schema_version '
            '(version INTEGER NOT NULL)'
        )
        row = connection.execute('SELECT MAX(version) FROM schema_version').fetchone()
        version = row[0] or 0

        if version < 2:
            employee_columns = _columns(connection, 'employees')
            if employee_columns:
                if 'rest_days' not in employee_columns:
                    connection.execute(
                        'ALTER TABLE employees ADD COLUMN rest_days TEXT DEFAULT ""'
                    )
                if 'min_rest_per_week' not in employee_columns:
                    connection.execute(
                        'ALTER TABLE employees ADD COLUMN min_rest_per_week INTEGER DEFAULT 2'
                    )

            record_columns = _columns(connection, 'attendance_records')
            if record_columns and 'late_notified' not in record_columns:
                connection.execute(
                    'ALTER TABLE attendance_records ADD COLUMN late_notified BOOLEAN DEFAULT 0'
                )

        connection.execute('DELETE FROM schema_version')
        connection.execute(
            'INSERT INTO schema_version(version) VALUES (?)',
            (LATEST_SCHEMA_VERSION,),
        )
        connection.commit()
