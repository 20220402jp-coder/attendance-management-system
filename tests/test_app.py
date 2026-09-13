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
    monkeypatch.setenv('SMTP_SERVER', 'developer.example.com')
    monkeypatch.setenv('SMTP_PASSWORD', 'developer-secret')
    module = load_app(tmp_path, monkeypatch)
    models = importlib.import_module('models')
    with module.app.app_context():
        assert models.Employee.query.count() == 0
        assert models.AttendanceRecord.query.count() == 0
        smtp_settings = models.Setting.query.all()
        assert len(smtp_settings) == len(module.SMTP_SETTING_KEYS)
        assert all(setting.value == '' for setting in smtp_settings)

    response = module.app.test_client().get('/api/settings')
    assert response.status_code == 200
    assert response.get_json() == {key: '' for key in module.SMTP_SETTING_KEYS}
    assert (tmp_path / 'data' / 'attendance.db').is_file()
    assert (tmp_path / 'data' / 'secret_key').is_file()


def test_main_pages_are_available(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    for path in ('/clock/access', '/admin/', '/admin/employees', '/admin/stats', '/schedule/'):
        assert client.get(path).status_code == 200


def test_removed_development_routes_stay_removed(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    assert client.post('/api/schedule/simulate').status_code == 404
    assert client.get('/download').status_code == 404


def test_employee_can_be_added_and_check_in_with_personal_code(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()

    response = client.post('/api/employee', json={
        'employee_id': 'E001',
        'name': '张三',
        'department': '全职',
        'lang': 'zh',
    })
    assert response.status_code == 200
    assert response.get_json()['ok'] is True

    assert client.post('/api/check', json={'employee_id':'E001','action':'check_in'}).status_code == 401
    authorize_clock(client, response.json['id'])
    response = client.post('/api/check', json={
        'employee_id': 'E001',
        'action': 'check_in',
    })
    assert response.status_code == 200
    assert response.get_json()['ok'] is True


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
        assert connection.execute('SELECT version FROM schema_version').fetchone()[0] == 3


def authorize_clock(client, eid):
    code = client.post(f'/api/employee/{eid}/schedule-code',json={}).json['code']
    assert client.post('/api/clock/access/login',json={'code':code}).json['ok']
    with client.session_transaction() as session:
        token=session['clock_token']
    client.environ_base['HTTP_X_CLOCK_TOKEN']=token
    return code
