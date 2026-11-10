import json
import re
from pathlib import Path

from test_app import load_app, authorize_clock

TRANSLATIONS = Path(__file__).resolve().parents[1] / 'attendance' / 'translations'
HAN = re.compile(r'[一-鿿]')


def load(lang):
    return json.loads((TRANSLATIONS / f'{lang}.json').read_text(encoding='utf-8'))


def test_all_languages_have_the_same_keys_and_placeholders():
    zh, en, ja = load('zh'), load('en'), load('ja')
    assert set(zh) == set(en) == set(ja)
    placeholder = re.compile(r'\{(\w+)\}')
    for key in zh:
        assert set(placeholder.findall(zh[key])) == set(placeholder.findall(en[key])) == set(placeholder.findall(ja[key])), key


def test_every_clock_style_is_translated(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    for lang in ('zh', 'en', 'ja'):
        t = load(lang)
        for theme in module.THEMES:
            for field in ('name', 'subtitle', 'animation'):
                assert t.get(f'theme.{theme}.{field}'), (lang, theme, field)


def test_english_pages_and_messages_contain_no_chinese(tmp_path, monkeypatch):
    module = load_app(tmp_path, monkeypatch)
    client = module.app.test_client()
    eid = client.post('/api/employee', json={'employee_id': 'E001', 'name': 'Alex'}).json['id']
    authorize_clock(client, eid)
    client.get('/set_lang/en')
    pages = ['/', '/clock/access', '/schedule/', '/admin/', '/admin/employees', '/admin/schedule', '/admin/stats',
             '/admin/settings', '/admin/attendance', '/admin/appearance', '/api/qrcode/print']
    pages += ['/admin/appearance/preview/' + theme for theme in module.THEMES]
    for path in pages:
        html = client.get(path + '?lang=en').get_data(as_text=True)
        text = re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>', ' ', html, flags=re.S)
        text = text.replace('中文', '').replace('日本語', '')
        assert not HAN.search(text), (path, HAN.findall(text)[:10])
    # server messages follow the language too
    authorize_clock(client, eid)
    msg = client.post('/api/clock/tickets?lang=en', json={'employee_id': 'E001', 'request_id': 'bad', 'action': 'check_in'}).json['msg']
    assert msg == 'Invalid request ID.'
    csv = client.post('/api/stats/export?lang=en', json={}).get_data(as_text=True)
    assert csv.lstrip('﻿').startswith('Date,Employee ID,Name')
