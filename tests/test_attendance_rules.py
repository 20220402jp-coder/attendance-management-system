"""主链路：新建员工 → 打卡 → 统计，以及考勤规则的各种边界。"""
import importlib
from datetime import date, datetime

from test_app import load_app, authorize_clock

MONDAY = date(2026, 11, 9)


def freeze(module, monkeypatch, moment):
    monkeypatch.setattr(module, 'today', lambda: moment.date())
    monkeypatch.setattr(module, 'now_dt', lambda: moment)


def add_employee(module, client, name='张三', kind='regular', created=date(2026, 1, 1), **extra):
    result = client.post('/api/employee', json={'name': name, 'employment_type': kind, **extra}).json
    assert result['ok'], result
    models = importlib.import_module('models')
    with module.app.app_context():
        models.db.session.get(models.Employee, result['id']).created_at = datetime.combine(created, datetime.min.time())
        models.db.session.commit()
    return result


def clock(client, employee_id, action):
    return client.post('/api/check', json={'employee_id': employee_id, 'action': action})


def rows(client, start, end, employee_id=None):
    return client.post('/api/stats', json={'employee_id': employee_id, 'start_date': start.isoformat(),
                                           'end_date': end.isoformat()}).json


def test_new_regular_employee_can_clock_in_on_a_weekday(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    emp = add_employee(module, client)
    assert emp['employee_id'] == 'E001' and len(emp['code']) == 4
    week = client.get(f"/api/employee/{emp['id']}/schedules").json
    assert [item['day_of_week'] for item in week] == [0, 1, 2, 3, 4]

    authorize_clock(client, emp['id'])
    freeze(module, monkeypatch, datetime(2026, 11, 10, 8, 55))  # a Tuesday
    today = client.get('/api/today/E001').json
    assert today['is_off'] is False and today['schedule']['start'] == '09:00'
    assert clock(client, 'E001', 'check_in').json['ok']
    freeze(module, monkeypatch, datetime(2026, 11, 10, 18, 5))
    assert clock(client, 'E001', 'check_out').json['ok']
    day = rows(client, date(2026, 11, 10), date(2026, 11, 10))
    assert [(r['status'], r['working_hours']) for r in day] == [('normal', 8.17)]


def test_rest_day_never_blocks_clocking(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    emp = add_employee(module, client, kind='part_time')
    assert client.get(f"/api/employee/{emp['id']}/schedules").json == []
    authorize_clock(client, emp['id'])
    freeze(module, monkeypatch, datetime(2026, 11, 15, 10, 0))  # Sunday, no shift at all
    assert client.get('/api/today/E001').json['is_off'] is True
    assert clock(client, 'E001', 'check_in').json['ok']
    freeze(module, monkeypatch, datetime(2026, 11, 15, 15, 30))
    assert clock(client, 'E001', 'check_out').json['ok']
    day = rows(client, date(2026, 11, 15), date(2026, 11, 15))
    # 10:00–15:30 minus the 12:00–13:00 lunch break
    assert [(r['status'], r['working_hours'], r['scheduled']) for r in day] == [('normal', 4.5, False)]


def test_absence_only_counts_scheduled_days_after_joining(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    add_employee(module, client, created=date(2026, 11, 4))  # joined on a Wednesday
    add_employee(module, client, name='兼职', kind='part_time')
    freeze(module, monkeypatch, datetime(2026, 11, 9, 8, 0))
    result = rows(client, date(2026, 10, 26), date(2026, 11, 12))
    # Regular: Wed 4, Thu 5, Fri 6 are absences; nothing before joining, no weekend, no future,
    # and Monday 9 is still "pending" at 08:00. The part-timer has no shifts, so no rows.
    assert [(r['date'], r['status']) for r in result] == [
        ('2026-11-04', 'absent'), ('2026-11-05', 'absent'), ('2026-11-06', 'absent'), ('2026-11-09', 'pending')]
    freeze(module, monkeypatch, datetime(2026, 11, 9, 9, 31))
    assert rows(client, MONDAY, MONDAY)[0]['status'] == 'absent'


def test_late_early_partial_and_summary(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    add_employee(module, client)
    for day, check_in, check_out in [('2026-11-02', '09:30', '18:00'), ('2026-11-03', '09:31', '18:00'),
                                     ('2026-11-04', '09:00', '17:00'), ('2026-11-05', '09:00', '')]:
        assert client.post('/api/attendance/update', json={
            'employee_id': 'E001', 'date': day, 'check_in': check_in, 'check_out': check_out}).json['ok']
    assert client.post('/api/attendance/update', json={'employee_id': 'E001', 'date': '2026-11-06', 'is_leave': True}).json['ok']
    freeze(module, monkeypatch, datetime(2026, 11, 9, 12, 0))
    result = rows(client, date(2026, 11, 2), date(2026, 11, 8))
    assert [r['status'] for r in result] == ['normal', 'late', 'early_leave', 'partial', 'leave']
    body = {'start_date': '2026-11-02', 'end_date': '2026-11-08'}
    person = client.post('/api/stats/monthly', json=body).json['employees'][0]
    assert (person['scheduled_days'], person['working_days'], person['late_count'], person['early_count'],
            person['partial_count'], person['leave_count'], person['absent_count']) == (5, 4, 1, 1, 1, 1, 0)
    assert person['total_hours'] == 21.98  # 7.5 + 7.48 + 7.0
    summary = client.post('/api/stats/export', json={**body, 'kind': 'summary'}).get_data(as_text=True)
    assert '21.98' in summary and '张三' in summary
    # the correction page shows the recomputed status too
    record = client.post('/api/attendance/records', json={'employee_id': 'E001', 'start_date': '2026-11-05',
                                                          'end_date': '2026-11-05'}).json['records'][0]
    assert record['status'] == 'partial'
    assert client.post('/api/stats', json={'start_date': '2026-11-08', 'end_date': '2026-11-02'}).status_code == 400


def test_part_time_hours_are_not_truncated_and_lunch_is_configurable(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    add_employee(module, client, kind='part_time')
    client.post('/api/attendance/update', json={'employee_id': 'E001', 'date': '2026-11-02',
                                                'check_in': '10:00', 'check_out': '18:54'})
    freeze(module, monkeypatch, datetime(2026, 11, 9, 12, 0))
    body = {'start_date': '2026-11-02', 'end_date': '2026-11-02'}
    assert ',7.90' in client.post('/api/stats/export', json=body).get_data(as_text=True)
    assert client.post('/api/rules', json={'lunch_enabled': False, 'grace_minutes': 5}).json['rules']['lunch_enabled'] is False
    assert ',8.90' in client.post('/api/stats/export', json=body).get_data(as_text=True)
    assert client.post('/api/rules', json={'work_start': 'nonsense'}).status_code == 400
    assert client.post('/api/rules', json={'grace_minutes': 999}).status_code == 400
    assert client.get('/api/rules').json['rules']['grace_minutes'] == 5


def test_late_reminder_placeholder_is_not_reported_as_normal(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    emp = add_employee(module, client)
    models = importlib.import_module('models')
    with module.app.app_context():
        # what the late-email checker leaves behind when someone never shows up
        models.db.session.add(models.AttendanceRecord(employee_id=emp['id'], date=date(2026, 11, 3), late_notified=True))
        models.db.session.commit()
    freeze(module, monkeypatch, datetime(2026, 11, 9, 12, 0))
    assert rows(client, date(2026, 11, 3), date(2026, 11, 3))[0]['status'] == 'absent'


def test_generated_schedule_decides_expected_days(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    regular = add_employee(module, client)
    part = add_employee(module, client, name='兼职', kind='part_time')
    models = importlib.import_module('models')
    with module.app.app_context():
        models.db.session.add_all([
            models.ScheduleAssignment(employee_id=regular['id'], date=date(2026, 11, 3), is_working=False),
            models.ScheduleAssignment(employee_id=part['id'], date=date(2026, 11, 7), is_working=True),
        ])
        models.db.session.commit()
    freeze(module, monkeypatch, datetime(2026, 11, 9, 12, 0))
    result = {(r['employee_id'], r['date']): r for r in rows(client, date(2026, 11, 2), date(2026, 11, 8))}
    assert ('E001', '2026-11-03') not in result          # rostered off on a weekday: not absent
    assert result[('E001', '2026-11-04')]['status'] == 'absent'
    assert result[('E002', '2026-11-07')]['status'] == 'absent'   # rostered on a Saturday
    assert result[('E002', '2026-11-07')]['shift'] == '09:00–18:00'
    assert len([key for key in result if key[0] == 'E002']) == 1


def test_employee_added_after_work_started_is_not_absent_that_day(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    emp = add_employee(module, client, created=MONDAY)
    models = importlib.import_module('models')
    with module.app.app_context():
        models.db.session.get(models.Employee, emp['id']).created_at = datetime(2026, 11, 9, 21, 0)
        models.db.session.commit()
    freeze(module, monkeypatch, datetime(2026, 11, 10, 8, 0))
    assert [(r['date'], r['status']) for r in rows(client, MONDAY, date(2026, 11, 10))] == [('2026-11-10', 'pending')]
