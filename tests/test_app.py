import importlib
import sqlite3
import sys


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv('ATTENDANCE_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('ATTENDANCE_LOG_DIR', str(tmp_path / 'logs'))
    for name in ('app', 'config', 'database', 'models'):
        sys.modules.pop(name, None)
    return importlib.import_module('app')


def test_new_installation_creates_empty_database(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    models = importlib.import_module('models')
    with module.app.app_context():
        assert models.Employee.query.count() == 0
        assert models.AttendanceRecord.query.count() == 0
    assert (tmp_path / 'data' / 'attendance.db').is_file()
    assert (tmp_path / 'data' / 'secret_key').is_file()


def test_main_pages_are_available(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    for path in ('/', '/admin/', '/admin/employees', '/admin/stats', '/schedule/'):
        assert client.get(path).status_code == 200


def test_removed_development_routes_stay_removed(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    assert client.post('/api/schedule/simulate').status_code == 404
    assert client.get('/download').status_code == 404


def test_legacy_database_is_upgraded_without_losing_employees(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    database = data_dir / 'attendance.db'
    with sqlite3.connect(database) as connection:
        connection.execute(
            'CREATE TABLE employees ('
            'id INTEGER PRIMARY KEY, employee_id VARCHAR(20) UNIQUE NOT NULL, '
            'name VARCHAR(100) NOT NULL, department VARCHAR(100), lang VARCHAR(5), '
            'pin_code VARCHAR(10), is_active BOOLEAN, created_at DATETIME)'
        )
        connection.execute(
            "INSERT INTO employees(employee_id, name) VALUES ('E001', '张三')"
        )
        connection.commit()

    module = load_app(tmp_path, monkeypatch)
    with module.app.app_context():
        models = importlib.import_module('models')
        assert models.Employee.query.count() == 1
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute('PRAGMA table_info(employees)')}
        assert {'rest_days', 'min_rest_per_week'} <= columns
        assert connection.execute('SELECT version FROM schema_version').fetchone()[0] == 2
