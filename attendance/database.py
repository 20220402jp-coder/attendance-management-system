"""数据库版本升级。"""

import sqlite3

from backup import make_backup
from config import DATABASE_PATH

# v1.0.4 及更早版本新建员工时误把默认班次建在周六、周日。
_BUGGY_DEFAULT = {(5, '09:00', '18:00', 0), (6, '09:00', '18:00', 0)}


def _repair_default_schedules(connection):
    """把从未改动过的错误默认班次（仅周六日）改成周一到周五。

    只处理正式员工且固定休息日仍是周六日的情况：这两项互相矛盾，
    可以确定是旧版本的默认值而不是管理员的设置。
    """
    employees = connection.execute(
        "SELECT id FROM employees WHERE employment_type = 'regular' "
        "AND COALESCE(rest_days, '') = '5,6'"
    ).fetchall()
    for (employee_id,) in employees:
        rows = {
            (row[0], row[1], row[2], int(bool(row[3])))
            for row in connection.execute(
                'SELECT day_of_week, start_time, end_time, is_off FROM schedules '
                'WHERE employee_id = ?', (employee_id,))
        }
        if rows != _BUGGY_DEFAULT:
            continue
        connection.execute('DELETE FROM schedules WHERE employee_id = ?', (employee_id,))
        connection.executemany(
            'INSERT INTO schedules(employee_id, day_of_week, start_time, end_time, is_off) '
            "VALUES (?, ?, '09:00', '18:00', 0)",
            [(employee_id, day) for day in range(5)],
        )


LATEST_SCHEMA_VERSION = 4


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
        tables = {item[0] for item in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        has_data = 'employees' in tables and connection.execute('SELECT COUNT(*) FROM employees').fetchone()[0] > 0
        if has_data and version < LATEST_SCHEMA_VERSION:
            connection.commit()
            make_backup('before-upgrade')

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

        if 'employees' in {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
            if 'employment_type' not in _columns(connection, 'employees'):
                connection.execute("ALTER TABLE employees ADD COLUMN employment_type TEXT NOT NULL DEFAULT 'part_time'")
                connection.execute("UPDATE employees SET employment_type = 'regular' WHERE instr(COALESCE(department, ''), '全职') > 0")

        if version < 4 and {'employees', 'schedules'} <= tables:
            _repair_default_schedules(connection)

        connection.execute('DELETE FROM schema_version')
        connection.execute(
            'INSERT INTO schema_version(version) VALUES (?)',
            (LATEST_SCHEMA_VERSION,),
        )
        connection.commit()
