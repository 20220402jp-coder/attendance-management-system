import importlib
import time
import uuid
from test_app import load_app, authorize_clock


def admin_headers(client):
    assert client.get('/admin/appearance').status_code == 200
    with client.session_transaction() as session:
        return {'X-Theme-CSRF': session['theme_csrf']}


def test_switch_preview_rollback_and_access(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    eid=client.post('/api/employee',json={'employee_id':'VIEW','name':'View'}).json['id']
    authorize_clock(client,eid)
    headers = admin_headers(client)
    assert client.get('/api/clock/theme').json['theme'] == 'classic'
    assert client.post('/admin/appearance', json={'theme': 'kimono', 'revision': 0}).status_code == 403
    assert client.get('/admin/appearance', environ_overrides={'REMOTE_ADDR': '192.168.1.20'}).status_code == 403
    assert client.get('/admin/appearance', headers={'Host': 'attacker.example'}).status_code == 403
    assert client.get('/admin/appearance/preview/kimono').status_code == 200
    assert client.get('/api/clock/theme').json['revision'] == 0
    assert client.get('/admin/appearance/preview/nope').status_code == 404
    assert client.post('/admin/appearance', headers=headers, json={'theme': '../index', 'revision': 0}).status_code == 400
    response = client.post('/admin/appearance', headers=headers, json={'theme': 'kimono', 'revision': 0})
    assert response.json['ok']
    assert b'kimono.css' in client.get('/').data
    assert client.get('/').headers['Cache-Control'] == 'no-store'
    assert client.post('/admin/appearance', headers=headers, json={'theme': 'classic', 'revision': 0}).status_code == 409
    assert client.post('/admin/appearance', headers=headers, json={'rollback': True, 'revision': 1}).json['theme'] == 'classic'
    assert b'kimono.css' not in client.get('/').data
    for path in ['/static/themes/character.js', '/static/themes/vendor/three.module.js', '/static/themes/vendor/three.core.js']:
        assert client.get(path).status_code == 200


def test_ticket_duplicate_and_result_survive_view_switch(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    models = importlib.import_module('models')
    client = module.app.test_client()
    eid=client.post('/api/employee', json={'employee_id': 'E001', 'name': '测试员工'}).json['id']
    authorize_clock(client,eid)
    data = {'request_id': str(uuid.uuid4()), 'employee_id': 'E001', 'action': 'check_in'}
    assert client.post('/api/clock/tickets', json={**data, 'action': 'bad'}).status_code == 400
    assert client.post('/api/clock/tickets', json=data).status_code == 202
    assert client.post('/api/clock/tickets', json=data).status_code == 202
    assert client.post('/api/clock/tickets', json={**data, 'action': 'check_out'}).status_code == 409
    for _ in range(100):
        result = client.get('/api/clock/tickets/' + data['request_id']).json
        if not result.get('pending'):
            break
        time.sleep(.02)
    assert result['result']['ok']
    headers = admin_headers(client)
    client.post('/admin/appearance', headers=headers, json={'theme': 'kimono', 'revision': 0})
    assert client.get('/api/today/E001').json['check_in'] == result['result']['time']
    assert client.post('/api/clock/tickets', json=data).status_code == 202
    with module.app.app_context():
        assert models.AttendanceRecord.query.count() == 1
        assert models.ClockTicket.query.count() == 1
    module._check_queue.put(None)


def test_restart_pending_ticket_is_resolved(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    models = importlib.import_module('models')
    tid = str(uuid.uuid4())
    client=module.app.test_client()
    eid=client.post('/api/employee',json={'employee_id':'removed','name':'Restart'}).json['id']
    authorize_clock(client,eid)
    with module.app.app_context():
        models.db.session.add(models.ClockTicket(id=tid, employee_id='removed', action='check_in', day=module.today().isoformat(), process_id='old'))
        models.db.session.commit()
    result = client.get('/api/clock/tickets/' + tid).json
    assert result['pending'] is False
    assert result['result']['ok'] is False


def test_all_designs_preview_apply_and_feedback(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    models = importlib.import_module('models')
    client = module.app.test_client()
    eid=client.post('/api/employee',json={'employee_id':'VIEW','name':'View'}).json['id']
    authorize_clock(client,eid)
    headers = admin_headers(client)
    assert len(module.CLOCK_THEMES) == 11
    revision = 0
    for theme in module.CLOCK_THEMES:
        preview = client.get('/admin/appearance/preview/' + theme)
        assert preview.status_code == 200
        assert b'id="success"' in preview.data
        assert b'id="modal-scene"' in preview.data
        assert b'"preview": true' in preview.data
        response = client.post('/admin/appearance', headers=headers, json={'theme': theme, 'revision': revision})
        assert response.json['ok']
        revision = response.json['revision']
        page = client.get('/')
        assert page.status_code == 200
        assert ('"theme": "' + theme + '"').encode() in page.data
        for asset in client.get('/api/clock/theme').json['assets'][theme]:
            assert client.get(asset).status_code == 200
    with module.app.app_context():
        assert models.AttendanceRecord.query.count() == 0
