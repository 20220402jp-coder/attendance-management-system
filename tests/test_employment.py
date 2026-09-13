import importlib
from test_app import load_app


def test_identity_independent_of_department(tmp_path, monkeypatch):
    app = load_app(tmp_path, monkeypatch)
    c = app.app.test_client()
    result = c.post('/api/employee', json={'employee_id':'ROLE1','name':'身份测试','department':'技术部','employment_type':'regular'})
    assert result.json['ok']
    eid = result.json['id']
    assert c.put(f'/api/employee/{eid}',json={'department':'销售部'}).json['ok']
    m = importlib.import_module('models')
    with app.app.app_context():
        assert m.db.session.get(m.Employee,eid).employment_type == 'regular'
    assert c.post('/api/schedule/auto',json={'default_min':0}).json['ok']
    employee = c.get('/api/schedule/result').json['employees'][0]
    assert all(day['working'] == (day['weekday'] < 5) for day in employee['days'])
    assert c.put(f'/api/employee/{eid}',json={'employment_type':'part_time'}).json['ok']
    assert c.put(f'/api/employee/{eid}',json={'employment_type':'invalid'}).status_code == 400
    with app.app.app_context():
        assert m.db.session.get(m.Employee,eid).employment_type == 'part_time'
        assert m.db.session.get(m.Employee,eid).department == '销售部'


def test_regular_priority_over_part_time_work_requests(tmp_path, monkeypatch):
    from datetime import date
    app = load_app(tmp_path, monkeypatch)
    monkeypatch.setattr(app, 'next_month_range', lambda: (date(2026,10,1), date(2026,10,7)))
    c = app.app.test_client()
    for eid,role in [('R','regular'),('P','part_time')]:
        added = c.post('/api/employee',json={'employee_id':eid,'name':eid,'employment_type':role}).json
        code = c.post(f"/api/employee/{added['id']}/schedule-code", json={}).json['code']
        token = c.post('/api/schedule/access/login', json={'employee_id':eid,'code':code}).json['token']
        prefs={f'2026-10-{d:02d}':('flexible' if eid=='R' else 'want_work') for d in range(1,8)}
        if eid=='R':prefs['2026-10-07']='want_off'
        c.post('/api/schedule/preferences',json={'employee_id':eid,'preferences':prefs}, headers={'X-Schedule-Token':token})
    assert c.post('/api/schedule/auto',json={'default_min':1}).json['ok']
    rows={e['employee_id']:e['days'] for e in c.get('/api/schedule/result').json['employees']}
    assert [d['working'] for d in rows['R']]==[True]*5+[False,False]
    assert [d['working'] for d in rows['P']]==[False]*5+[True,True]
    # With a shortfall, part-time employees fill the remaining place.
    assert c.post('/api/schedule/auto',json={'default_min':2}).json['ok']
    rows={e['employee_id']:e['days'] for e in c.get('/api/schedule/result').json['employees']}
    assert rows['R'][0]['working'] and rows['P'][0]['working']
