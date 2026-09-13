import importlib
from test_app import load_app


def setup_access(tmp_path, monkeypatch):
    app = load_app(tmp_path, monkeypatch)
    c = app.app.test_client()
    ids = [c.post('/api/employee', json={'employee_id':x,'name':x}).json['id'] for x in ('A','B')]
    code = c.post(f'/api/employee/{ids[0]}/schedule-code', json={}).json['code']
    return app, c, ids, code


def login(c, code):
    return c.post('/api/schedule/access/login', json={'employee_id':'A','code':code})


def test_own_only_and_save_revokes_session(tmp_path, monkeypatch):
    app,c,ids,code = setup_access(tmp_path,monkeypatch)
    assert len(code)==3 and code.isdigit()
    assert c.get('/api/schedule/preferences/A').status_code==401
    h={'X-Schedule-Token':login(c,code).json['token']}
    assert c.get('/api/schedule/preferences/A',headers=h).json['ok']
    assert c.get('/api/schedule/preferences/B',headers=h).status_code==403
    day=app.next_month_range()[0].isoformat()
    payload={'employee_id':'B','preferences':{day:'want_off'}}
    assert c.post('/api/schedule/preferences',json=payload,headers=h).status_code==403
    payload['employee_id']='A'
    assert c.post('/api/schedule/preferences',json=payload,headers=h).json['ok']
    assert c.get('/api/schedule/preferences/A',headers=h).status_code==401
    h={'X-Schedule-Token':login(c,code).json['token']}
    assert c.get('/api/schedule/preferences/A',headers=h).json['preferences'][day]=='want_off'
    assert c.post('/api/schedule/access/logout',headers=h).json['ok']
    assert c.get('/api/schedule/preferences/A',headers=h).status_code==401


def test_lockout_persists_across_clients_and_reset_revokes(tmp_path,monkeypatch):
    app,c,ids,code=setup_access(tmp_path,monkeypatch)
    h={'X-Schedule-Token':login(c,code).json['token']}
    wrong=f'{(int(code)+1)%1000:03d}'
    for i in range(5):
        assert login(app.app.test_client(),wrong).status_code==(429 if i==4 else 403)
    assert login(c,code).status_code==429
    new=c.post(f'/api/employee/{ids[0]}/schedule-code',json={}).json['code']
    assert new!=code
    assert c.get('/api/schedule/preferences/A',headers=h).status_code==401
    assert login(c,code).status_code==403
    assert login(c,new).json['ok']


def test_expiry_inactive_and_leading_zero(tmp_path,monkeypatch):
    app,c,ids,code=setup_access(tmp_path,monkeypatch)
    monkeypatch.setattr(app.secrets,'randbelow',lambda _:7)
    code=c.post(f'/api/employee/{ids[0]}/schedule-code',json={}).json['code'] if code!='007' else code
    assert code=='007'
    h={'X-Schedule-Token':login(c,code).json['token']}
    m=importlib.import_module('models')
    with app.app.app_context():
        for row in m.ScheduleSession.query.all():row.last_active-=301
        m.db.session.commit()
    assert c.post('/api/schedule/access/keepalive',headers=h).status_code==401
    h={'X-Schedule-Token':login(c,code).json['token']}
    c.put(f'/api/employee/{ids[0]}',json={'is_active':False})
    assert c.get('/api/schedule/preferences/A',headers=h).status_code==401
    assert login(c,code).status_code==403
