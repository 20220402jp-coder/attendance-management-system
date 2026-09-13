import importlib
import uuid
from test_app import load_app, authorize_clock


def test_code_only_privacy_and_all_clock_routes(tmp_path,monkeypatch):
    m=load_app(tmp_path,monkeypatch);c=m.app.test_client()
    a=c.post('/api/employee',json={'employee_id':'A','name':'Only Me'}).json['id']
    b=c.post('/api/employee',json={'employee_id':'B','name':'Secret Other'}).json['id']
    assert c.get('/').status_code==302
    assert b'Secret Other' not in c.get('/clock/access').data
    code=authorize_clock(c,a)
    for theme in m.CLOCK_THEMES:
        # Set the theme through the existing local administrative interface.
        with m.app.app_context():m.Setting.set('clock_theme',__import__('json').dumps({'theme':theme,'revision':0}))
        page=c.get('/')
        assert page.status_code==200
        assert b'Secret Other' not in page.data
        assert b'Only Me' in page.data
    for path in ['/api/check','/api/clock/tickets']:
        assert c.post(path,json={'employee_id':'B','action':'check_in','request_id':str(uuid.uuid4())}).status_code==403
    assert c.get('/api/today/B').status_code==403
    models=importlib.import_module('models');tid=str(uuid.uuid4())
    with m.app.app_context():
        models.db.session.add(models.ClockTicket(id=tid,employee_id='B',action='check_in',day=m.today().isoformat()))
        models.db.session.commit()
    assert c.get('/api/clock/tickets/'+tid).status_code==403
    assert '/clock/access' in c.get('/api/server-info').json['url']
    assert b'/clock/access' in c.get('/api/qrcode/print').data
    assert c.post('/api/clock/access/logout').json['ok']
    assert c.get('/api/today/A').status_code==401
    assert c.get('/').status_code==302


def test_unique_codes_expiry_reset_and_guess_limit(tmp_path,monkeypatch):
    m=load_app(tmp_path,monkeypatch);c=m.app.test_client()
    a=c.post('/api/employee',json={'employee_id':'A','name':'A'}).json['id']
    b=c.post('/api/employee',json={'employee_id':'B','name':'B'}).json['id']
    monkeypatch.setattr(m.secrets,'randbelow',lambda _:7)
    code=authorize_clock(c,a);assert code=='007'
    other=c.post(f'/api/employee/{b}/schedule-code',json={}).json['code'];assert other!='007'
    models=importlib.import_module('models')
    with m.app.app_context():
        models.ClockSession.query.first().last_active-=301;models.db.session.commit()
    assert c.get('/api/today/A').status_code==401
    assert c.post('/api/clock/access/login',json={'code':code}).json['ok']
    with c.session_transaction() as s:c.environ_base['HTTP_X_CLOCK_TOKEN']=s['clock_token']
    c.post(f'/api/employee/{a}/schedule-code',json={})
    assert c.get('/api/today/A').status_code==401
    for i in range(5):assert c.post('/api/clock/access/login',json={'code':'999'}).status_code==(429 if i==4 else 403)
    assert m.app.test_client().post('/api/clock/access/login',json={'code':other}).status_code==429
