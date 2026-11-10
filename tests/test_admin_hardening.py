"""后台仅本机、个人码、员工管理、备份、升级修复、端口。"""
import importlib
import sqlite3
from datetime import date, datetime

from werkzeug.security import generate_password_hash

from test_app import load_app, authorize_clock
from test_attendance_rules import add_employee, clock, freeze, rows

LAN = {'REMOTE_ADDR': '192.168.1.50'}


def test_overnight_checkout_and_forgotten_checkout(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    emp = add_employee(module, client, kind='part_time')
    authorize_clock(client, emp['id'])
    freeze(module, monkeypatch, datetime(2026, 11, 2, 18, 0))
    assert clock(client, 'E001', 'check_in').json['ok']
    # closing after midnight still belongs to the 2nd
    freeze(module, monkeypatch, datetime(2026, 11, 3, 1, 30))
    assert client.get('/api/today/E001').json['overnight'] is True
    assert clock(client, 'E001', 'check_out').json['ok']
    # the same afternoon: a fresh day
    freeze(module, monkeypatch, datetime(2026, 11, 3, 18, 0))
    assert client.get('/api/today/E001').json['check_in'] is None
    assert clock(client, 'E001', 'check_in').json['ok']
    # forgot to check out; next morning must offer check-in, not yesterday's check-out
    freeze(module, monkeypatch, datetime(2026, 11, 4, 9, 0))
    assert client.get('/api/today/E001').json['check_in'] is None
    assert clock(client, 'E001', 'check_out').status_code == 400
    assert clock(client, 'E001', 'check_in').json['ok']
    result = rows(client, date(2026, 11, 2), date(2026, 11, 4))
    assert [(r['date'], r['status'], r['working_hours']) for r in result] == [
        ('2026-11-02', 'normal', 7.5), ('2026-11-03', 'partial', None), ('2026-11-04', 'working', None)]
    assert result[0]['check_out'].endswith('(+1)')


def test_overnight_shift_defined_in_weekly_hours(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    emp = add_employee(module, client, kind='part_time')
    assert client.post(f"/api/employee/{emp['id']}/schedules", json={'schedules': [
        {'day_of_week': 0, 'start_time': '22:00', 'end_time': '06:00', 'is_off': False}]}).json['ok']
    assert client.post(f"/api/employee/{emp['id']}/schedules", json={'schedules': [{'day_of_week': 9}]}).status_code == 400
    authorize_clock(client, emp['id'])
    freeze(module, monkeypatch, datetime(2026, 11, 9, 21, 55))
    assert clock(client, 'E001', 'check_in').json['ok']
    freeze(module, monkeypatch, datetime(2026, 11, 10, 6, 5))
    assert client.get('/api/today/E001').json['overnight'] is True
    assert clock(client, 'E001', 'check_out').json['ok']
    result = rows(client, date(2026, 11, 9), date(2026, 11, 10))
    assert [(r['date'], r['status'], r['working_hours']) for r in result] == [('2026-11-09', 'normal', 8.17)]


def test_admin_is_local_only_but_clocking_is_not(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    add_employee(module, client)
    for path in ['/admin/', '/admin/employees', '/admin/stats', '/admin/settings', '/admin/attendance',
                 '/admin/schedule', '/api/settings', '/api/rules', '/api/dashboard/today', '/api/backup/download',
                 '/api/server-info', '/api/qrcode/print', '/api/schedule/result', '/api/employee/1/schedules']:
        assert client.get(path, environ_overrides=LAN).status_code == 403, path
        assert client.get(path, headers={'Host': 'attacker.example'}).status_code == 403, path
    for path, body in [('/api/employee', {'name': 'x'}), ('/api/stats', {}), ('/api/stats/export', {}),
                       ('/api/attendance/update', {'employee_id': 'E001', 'date': '2026-11-02', 'check_in': '09:00'}),
                       ('/api/employee/1/schedule-code', {}), ('/api/schedule/auto', {}), ('/api/settings', {})]:
        assert client.post(path, json=body, environ_overrides=LAN).status_code == 403, path
    assert client.delete('/api/employee/1', environ_overrides=LAN).status_code == 403
    assert client.put('/api/employee/1', json={'name': 'x'}, environ_overrides=LAN).status_code == 403
    # another website open in the admin's own browser cannot submit changes either
    assert client.post('/api/employee', json={'name': 'x'}, headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.post('/api/employee', json={'name': '李四'}, headers={'Origin': 'http://localhost:5000'}).status_code == 200
    # employees on the LAN can still reach everything they need
    for path in ['/clock/access', '/schedule/', '/api/clock/theme', '/static/style.css']:
        assert client.get(path, environ_overrides=LAN).status_code == 200, path
    assert client.get('/', environ_overrides=LAN).status_code == 302
    assert client.post('/api/clock/access/login', json={'code': '12'}, environ_overrides=LAN).status_code == 400


def test_employee_form_rules(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    assert client.post('/api/employee', json={'name': '  '}).status_code == 400
    first = client.post('/api/employee', json={'name': '甲', 'employee_id': 'A1'}).json
    duplicate = client.post('/api/employee', json={'name': '乙', 'employee_id': 'A1'})
    assert duplicate.status_code == 409 and 'A1' in duplicate.json['msg']
    second = client.post('/api/employee', json={'name': '乙'}).json
    assert second['employee_id'] == 'E002' and second['code'] != first['code']
    # with records: cannot delete, can be marked as left, and still shows in that month's export
    client.post('/api/attendance/update', json={'employee_id': 'A1', 'date': '2026-11-02',
                                                'check_in': '09:00', 'check_out': '18:00'})
    assert client.delete(f"/api/employee/{first['id']}").status_code == 409
    assert client.put(f"/api/employee/{first['id']}", json={'is_active': False}).json['ok']
    freeze(module, monkeypatch, datetime(2026, 11, 9, 12, 0))
    result = rows(client, date(2026, 11, 2), date(2026, 11, 6))
    assert [(r['employee_id'], r['date']) for r in result if r['employee_id'] == 'A1'] == [('A1', '2026-11-02')]
    assert client.post('/api/clock/access/login', json={'code': first['code']}).status_code == 403
    # without records: deletion works and leaves a backup behind
    assert client.delete(f"/api/employee/{second['id']}").json['ok']
    assert list((tmp_path / 'data' / 'backups').glob('attendance-*-before-delete.db'))


def test_legacy_three_digit_code_and_gentler_lockout(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    emp = add_employee(module, client)
    models = importlib.import_module('models')
    with module.app.app_context():
        models.db.session.get(models.ScheduleAccess, emp['id']).code_hash = generate_password_hash('042')
        models.db.session.commit()
    assert client.post('/api/clock/access/login', json={'code': '042'}).json['ok']
    assert client.post('/api/schedule/access/login', json={'employee_id': 'E001', 'code': '042'}).json['ok']
    clock_now = [1_000_000.0]
    monkeypatch.setattr(module.time_module, 'time', lambda: clock_now[0])
    for attempt in range(5):
        status = client.post('/api/clock/access/login', json={'code': '9999'}).status_code
        assert status == (429 if attempt == 4 else 403)
    clock_now[0] += 59
    assert client.post('/api/clock/access/login', json={'code': '042'}).status_code == 429
    clock_now[0] += 2  # first lock lasts one minute, not ten
    for attempt in range(5):
        status = client.post('/api/clock/access/login', json={'code': '9999'}).status_code
        assert status == (429 if attempt == 4 else 403)
    clock_now[0] += 61  # the second lock is longer
    assert client.post('/api/clock/access/login', json={'code': '042'}).status_code == 429
    clock_now[0] += 60
    assert client.post('/api/clock/access/login', json={'code': '042'}).json['ok']


def test_dashboard_backup_and_qr_warning(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    emp = add_employee(module, client)
    add_employee(module, client, name='李四')
    authorize_clock(client, emp['id'])
    client.post('/api/attendance/update', json={'employee_id': 'E002', 'date': '2026-11-09', 'check_in': '09:00'})
    freeze(module, monkeypatch, datetime(2026, 11, 10, 9, 45))
    assert clock(client, 'E001', 'check_in').json['ok']
    board = client.get('/api/dashboard/today').json
    assert [(r['name'], r['status'], r['late']) for r in board['rows']] == [('张三', 'working', True), ('李四', 'absent', False)]
    assert [(r['name'], r['status']) for r in board['attention']] == [('张三', 'absent'), ('李四', 'partial')]
    assert board['qr_changed'] is False and board['last_backup'] == ''
    download = client.get('/api/backup/download')
    assert download.status_code == 200 and download.data.startswith(b'SQLite format 3')
    assert client.get('/api/dashboard/today').json['last_backup']
    backup = importlib.import_module('backup')
    assert backup.backup_if_due() is None  # already backed up today
    # showing the QR code remembers its address; a different address later raises the warning
    monkeypatch.setattr(module, 'get_lan_ip', lambda: '192.168.1.10')
    assert client.get('/api/server-info?remember=1').json['app'] == 'attendance-system'
    assert client.get('/api/dashboard/today').json['qr_changed'] is False
    monkeypatch.setattr(module, 'get_lan_ip', lambda: '192.168.1.77')
    assert client.get('/api/dashboard/today').json['qr_changed'] is True


def test_upgrade_repairs_weekend_only_default_and_backs_up(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    emp = add_employee(module, client)
    custom = add_employee(module, client, name='周末兼职', kind='part_time')
    database = tmp_path / 'data' / 'attendance.db'
    with sqlite3.connect(database) as connection:  # recreate what v1.0.4 wrote
        connection.execute('DELETE FROM schedules')
        for employee in (emp['id'], custom['id']):
            connection.executemany("INSERT INTO schedules(employee_id, day_of_week, start_time, end_time, is_off) "
                                   "VALUES (?, ?, '09:00', '18:00', 0)", [(employee, 5), (employee, 6)])
        connection.execute('UPDATE schema_version SET version = 3')
        connection.commit()
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    assert [s['day_of_week'] for s in client.get(f"/api/employee/{emp['id']}/schedules").json] == [0, 1, 2, 3, 4]
    assert [s['day_of_week'] for s in client.get(f"/api/employee/{custom['id']}/schedules").json] == [5, 6]
    assert list((tmp_path / 'data' / 'backups').glob('attendance-*-before-upgrade.db'))


def test_port_falls_back_when_taken(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    monkeypatch.setattr(module, 'port_is_free', lambda port: port not in (5000, 5001))
    assert module.choose_port(5000) == 5002
    assert module.choose_port(5010) == 5010
    monkeypatch.setenv('ATTENDANCE_PORT', '80')
    assert module.preferred_port() == 5000
