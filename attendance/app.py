import json
from html import escape as html_escape
import secrets
import hashlib
import hmac
from werkzeug.security import check_password_hash
import os
import csv
import io
import socket
import calendar
import random
import smtplib
import uuid
import time as time_module
import threading
import urllib.request
import urllib.parse
import queue as queue_module
from datetime import date, datetime, timedelta
from functools import lru_cache
from email.mime.text import MIMEText

from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, send_file)
from dateutil import parser as dtparser

from config import Config, BASE_DIR, DATA_DIR
from database import run_migrations
from logging_config import setup_logging
from models import (db, Employee, Schedule, AttendanceRecord,
                    SchedulePreference, ScheduleAssignment, Setting, ScheduleAccess, ScheduleSession, ClockSession, ClockAccessAttempt)
from rules import (ShiftBook, clean_rules, evaluate, get_rules,
                   overnight_open)
import backup as backup_module
from version import APP_NAME, APP_VERSION

CLOCK_PROCESS_ID = uuid.uuid4().hex
DEFAULT_PORT = 5000
SERVER_PORT = DEFAULT_PORT  # 启动时可能改为其他空闲端口
os.environ['ATTENDANCE_PROCESS_ID'] = CLOCK_PROCESS_ID

# ── App factory ───────────────────────────────────────────────────

logger = setup_logging(
    os.environ.get('ATTENDANCE_LOG_DIR', os.path.join(DATA_DIR, 'logs'))
)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

SMTP_SETTING_KEYS = (
    'smtp_server',
    'smtp_port',
    'smtp_user',
    'smtp_password',
    'admin_email',
    'email_from',
    'late_notify_minutes',
)


def first_run_setup():
    """创建空数据库和全部数据表。

    该操作可重复执行，不会添加示例员工或改动已有数据。
    """
    db_path = os.path.join(DATA_DIR, 'attendance.db')
    is_new_database = not os.path.exists(db_path)
    with app.app_context():
        db.create_all()
        if is_new_database:
            db.session.add_all(Setting(key=key, value='') for key in SMTP_SETTING_KEYS)
            db.session.commit()
    run_migrations()
    if is_new_database:
        logger.info('已创建空数据库: %s', db_path)


first_run_setup()


# ── i18n ───────────────────────────────────────────────────────────

TRANSLATIONS_DIR = os.path.join(BASE_DIR, 'translations')

# ── Check-in Queue ────────────────────────────────────────────────
# Ensures orderly processing when many employees check in at once.
_check_queue = queue_module.Queue()
_check_results = {}
_check_results_lock = threading.Lock()
_check_worker_running = False
_check_worker_lock = threading.Lock()

# 全局写入锁：排队打卡 + 管理端修改 串行化，防止数据覆盖
_write_lock = threading.Lock()

def _check_worker():
    """Background worker: processes check-in/out requests one by one."""
    while True:
        try:
            job = _check_queue.get(timeout=60)
        except queue_module.Empty:
            continue
        if job is None:
            break
        job_id = job['job_id']
        try:
            with _write_lock:
                with app.app_context():
                    from models import ClockTicket
                    ticket = db.session.get(ClockTicket, job_id) if job.get('ticket') else None
                    result = ({'ok': False, 'msg': tmsg('msg.day_changed', job.get('lang', 'zh'))}
                              if ticket and ticket.day != today().isoformat()
                              else _process_check(job['data'], job.get('lang', 'zh')))
                    if job.get('ticket'):
                        from models import ClockTicket
                        ticket = db.session.get(ClockTicket, job['job_id'])
                        ticket.result = json.dumps(result)
                        db.session.commit()
            if not job.get('ticket'):
                with _check_results_lock:
                    _check_results[job_id] = result
        except Exception as e:
            if job.get('ticket'):
                with app.app_context():
                    from models import ClockTicket
                    db.session.rollback()
                    ticket = db.session.get(ClockTicket, job_id)
                    if ticket:
                        ticket.result = json.dumps({'ok': False, 'msg': tmsg('msg.process_failed', job.get('lang', 'zh'))})
                        db.session.commit()
            else:
                with _check_results_lock:
                    _check_results[job_id] = {'ok': False, 'msg': str(e)}
        finally:
            _check_queue.task_done()

def _ensure_check_worker():
    global _check_worker_running
    with _check_worker_lock:
        if not _check_worker_running:
            t = threading.Thread(target=_check_worker, daemon=True)
            t.start()
            _check_worker_running = True

def current_record(emp, now, day, book):
    """返回 (记录, 记录所属日期)。

    凌晨为前一天的班次签退时，记录属于前一天，而不是今天。
    """
    record = AttendanceRecord.query.filter_by(employee_id=emp.id, date=day).first()
    if record is None or not record.check_in:
        previous_day = day - timedelta(days=1)
        previous = AttendanceRecord.query.filter_by(employee_id=emp.id, date=previous_day).first()
        if (previous is not None and previous.check_in and not previous.check_out
                and previous.status != 'leave'
                and overnight_open(previous_day, book.shift(emp, previous_day), now)):
            return previous, previous_day
    return record, day


def stored_status(outcome):
    """写入数据库的状态。页面显示一律重新计算，这里只为兼容旧数据。"""
    status = outcome['status']
    if status in ('working', 'pending', None):
        return 'late' if outcome['late'] else 'normal'
    return status


def apply_outcome(record, emp, day, book, now):
    outcome = evaluate(record, book.shift(emp, day), book.rules, now, day)
    record.working_hours = outcome['hours']
    record.status = stored_status(outcome)
    return outcome


def _process_check(data, lang):
    """Core check-in/out logic (runs in worker thread with app context).

    休息日和未排班的日子同样可以打卡：系统只记录事实，不拦人。
    """
    t = load_translations(lang)
    employee_id = data.get('employee_id')
    action = data.get('action', 'check_in')

    emp = Employee.query.filter_by(employee_id=employee_id, is_active=True).first()
    if not emp:
        return {'ok': False, 'msg': t['error.employee_not_found'], '_code': 404}

    dt_today = today()
    now = now_dt()
    book = ShiftBook([emp.id], dt_today - timedelta(days=1), dt_today)
    record, record_day = current_record(emp, now, dt_today, book)

    try:
        if action == 'check_in':
            if record is not None and record.check_in:
                return {'ok': False, 'msg': t['home.already_checked_in'], '_code': 400}
            if record is None:
                record = AttendanceRecord(employee_id=emp.id, date=record_day)
                db.session.add(record)
            record.check_in = now
            record.status = 'normal'  # 打卡即到岗，覆盖之前的请假/缺勤标记
        elif action == 'check_out':
            if record is None or not record.check_in:
                return {'ok': False, 'msg': t['msg.check_in_first'], '_code': 400}
            if record.check_out:
                return {'ok': False, 'msg': t['home.already_checked_out'], '_code': 400}
            record.check_out = now
        else:
            return {'ok': False, 'msg': t['msg.bad_action'], '_code': 400}

        apply_outcome(record, emp, record_day, book, now)
        db.session.commit()

        msg = t['home.check_in_success'] if action == 'check_in' else t['home.check_out_success']
        return {
            'ok': True,
            'msg': msg,
            'time': now.strftime('%H:%M:%S'),
            'check_in': record.check_in.strftime('%H:%M:%S') if record.check_in else None,
            'check_out': record.check_out.strftime('%H:%M:%S') if record.check_out else None,
        }
    except Exception:
        db.session.rollback()
        logger.exception('打卡处理失败: %s', employee_id)
        return {'ok': False, 'msg': t['msg.process_failed']}


def tmsg(key, lang=None, **kw):
    """Translated message for API responses; falls back to the key itself."""
    text = load_translations(lang or get_lang()).get(key, key)
    return text.format(**kw) if kw else text


# Schedule notes are stored as stable codes; older rows may still contain Chinese text.
SCHEDULE_NOTE_CODES = {'偏好休息但排班': 'pref_off_assigned', '都可': 'flexible', '未提交偏好': 'no_pref',
                       '偏好上班但调整': 'pref_work_adjusted', '偏好休息': 'pref_off', '手动调整': 'manual'}


def schedule_note_label(note, lang=None):
    code = SCHEDULE_NOTE_CODES.get(note, note)
    key = 'note.' + code if code else ''
    translations = load_translations(lang or get_lang())
    return translations.get(key, note) if key else ''


@lru_cache(maxsize=3)
def load_translations(lang):
    path = os.path.join(TRANSLATIONS_DIR, f'{lang}.json')
    if not os.path.exists(path):
        path = os.path.join(TRANSLATIONS_DIR, 'zh.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_lang():
    """Get language: session > cookie > employee pref > default."""
    lang = request.args.get('lang')
    if lang and lang in ('zh', 'en', 'ja'):
        return lang
    lang = session.get('lang')
    if lang and lang in ('zh', 'en', 'ja'):
        return lang
    lang = request.cookies.get('lang')
    if lang and lang in ('zh', 'en', 'ja'):
        return lang
    return 'zh'


@app.context_processor
def inject_globals():
    lang = get_lang()
    t = load_translations(lang)
    return {
        '_': lambda key, **kw: t.get(key, key).format(**kw) if kw else t.get(key, key),
        'translations': t,
        'current_lang': lang,
        'langs': [('zh', '中文'), ('en', 'English'), ('ja', '日本語')],
        'now': datetime.now(),
        'is_admin': request.path.startswith('/admin'),
        'is_schedule': request.path == '/schedule/',
        'body_class': '' if request.path.startswith('/admin') or request.path == '/schedule/' else 'clock-page-body',
    }


# ── Helper ─────────────────────────────────────────────────────────

def today():
    return date.today()


def now_dt():
    return datetime.now()


def get_lan_ip():
    """Detect the LAN IP of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # doesn't need to reachable
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


# ── Routes: Clock in/out ─────────────────────────────────────────


# Shared clock views; one configuration record makes selection/revision atomic.
from theme_catalog import THEMES
CLOCK_THEMES = {key: value['template'] for key, value in THEMES.items()}
CLOCK_ASSETS_VERSION = '1'

def clock_theme_config():
    try:
        value = json.loads(Setting.get('clock_theme', '{}'))
        if value.get('theme') in CLOCK_THEMES and type(value.get('revision')) is int:
            if value['theme'] == 'kimono' and not all(os.path.isfile(os.path.join(BASE_DIR, path)) for path in ('templates/clock_kimono.html', 'static/themes/kimono.css', 'static/themes/character.js')):
                return {**value, 'theme': 'classic'}
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    return {'theme': 'classic', 'revision': 0, 'previous': None}

LOCAL_HOSTS = ('127.0.0.1', 'localhost', '::1')
# 员工在手机或共用平板上需要用到的地址；除此之外全部只允许本机访问。
PUBLIC_EXACT = {'/', '/schedule', '/schedule/', '/api/check'}
PUBLIC_PREFIXES = ('/static/', '/clock/access', '/api/clock/', '/api/today/', '/set_lang/',
                   '/api/schedule/access/', '/api/schedule/preferences')


def is_local_request():
    """请求来自运行程序的这台电脑，并且是用本机地址打开的。"""
    host = urllib.parse.urlsplit(request.host_url).hostname
    return request.remote_addr in ('127.0.0.1', '::1') and host in LOCAL_HOSTS


local_theme_admin = is_local_request


@app.before_request
def admin_is_local_only():
    """管理后台和全部管理接口只在本机开放。

    系统没有管理员账号；局域网里的手机只能打卡和报班，
    不能打开后台，也不能直接调用管理接口。
    """
    path = request.path
    if path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIXES):
        return None
    if not is_local_request():
        if path.startswith('/api/'):
            return jsonify(ok=False, msg=tmsg('admin.local_only')), 403
        return tmsg('admin.local_only'), 403
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        # 本机浏览器打开的其他网站不能代替管理员提交修改。
        origin = request.headers.get('Origin')
        if origin and urllib.parse.urlsplit(origin).hostname not in LOCAL_HOSTS:
            return jsonify(ok=False, msg=tmsg('admin.local_only')), 403
    return None


def localized_themes():
    translations = load_translations(get_lang())
    return {key: {**item, **{field: translations.get(f'theme.{key}.{field}', item[field])
            for field in ('name', 'subtitle', 'animation')}} for key, item in THEMES.items()}

def render_clock(theme, employees, config, preview):
    boot = {'theme': theme, 'revision': config['revision'], 'preview': preview,
            'lang': get_lang(), 'day': today().isoformat(), 'assetVersion': CLOCK_ASSETS_VERSION,
            'token': '' if preview else session.get('clock_token', ''),
            'employeeId': employees[0].employee_id if employees else '',
            'exitLabel': load_translations(get_lang())['clock_access.exit']}
    response = app.make_response(render_template(CLOCK_THEMES[theme], employees=employees, clock_boot=boot, design=localized_themes()[theme]))
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/api/clock/theme')
def api_clock_theme():
    shared = ['/static/themes/clock.js?v=5', '/static/themes/feedback.css?v=2', '/static/themes/feedback-fx.js?v=1']
    three = ['/static/themes/vendor/three.module.js', '/static/themes/vendor/three.core.js']
    assets = {key: ['/static/themes/collection.css?v=1', *shared] for key in THEMES}
    assets['original'] = ['/static/style.css', *shared]
    assets['classic'] = ['/static/style.css', '/static/themes/cyber.js?v=1', *three, *shared]
    assets['kimono'] = ['/static/themes/kimono.css?v=2', '/static/themes/character.js?v=2', '/static/themes/clock.js?v=5', '/static/themes/feedback-fx.js?v=1']
    assets['planet'] = ['/static/themes/planet.css?v=1', '/static/themes/planet.js?v=1', *three, *shared]
    response = jsonify(**clock_theme_config(), day=today().isoformat(), assets=assets)
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/admin/appearance', methods=['GET', 'POST'])
def admin_appearance():
    if not local_theme_admin():
        return load_translations(get_lang())['appearance.local'], 403
    if request.method == 'POST':
        if (not session.get('theme_csrf') or
                request.headers.get('X-Theme-CSRF') != session['theme_csrf']):
            return jsonify(ok=False, msg=load_translations(get_lang())['appearance.expired']), 403
        data = request.get_json(silent=True) or {}
        with _write_lock:
            current = clock_theme_config()
            if data.get('revision') != current['revision']:
                return jsonify(ok=False, msg=load_translations(get_lang())['appearance.conflict']), 409
            theme = current.get('previous') if data.get('rollback') else data.get('theme')
            if theme not in CLOCK_THEMES:
                return jsonify(ok=False, msg=load_translations(get_lang())['appearance.invalid']), 400
            if theme != current['theme']:
                current = {'theme': theme, 'previous': current['theme'], 'revision': current['revision'] + 1}
                Setting.set('clock_theme', json.dumps(current))
                logger.info('本机应用打卡样式: %s，版本: %s', theme, current['revision'])
        return jsonify(ok=True, **current)
    session.setdefault('theme_csrf', uuid.uuid4().hex)
    return render_template('admin_appearance.html', theme_config=clock_theme_config(), csrf=session['theme_csrf'], themes=localized_themes())

@app.route('/admin/appearance/preview/<theme>')
def appearance_preview(theme):
    if not local_theme_admin():
        return load_translations(get_lang())['appearance.local_preview'], 403
    if theme not in CLOCK_THEMES:
        return load_translations(get_lang())['appearance.not_found'], 404
    from types import SimpleNamespace
    employees = [SimpleNamespace(employee_id='PREVIEW', name=load_translations(get_lang())['appearance.demo_name'], department=load_translations(get_lang())['appearance.demo_dept'], is_active=True)]
    return render_clock(theme, employees, clock_theme_config(), True)

@app.route('/api/clock/tickets', methods=['POST'])
def create_clock_ticket():
    emp = clock_identity()
    if not emp:
        return schedule_error('expired', 401)
    if (request.get_json(silent=True) or {}).get('employee_id') != emp.employee_id:
        return schedule_error('own_only', 403)
    from models import ClockTicket
    data = request.get_json(silent=True) or {}
    tid = data.get('request_id', '')
    try:
        uuid.UUID(tid)
    except (ValueError, TypeError, AttributeError):
        return jsonify(ok=False, msg=tmsg('msg.bad_request_id')), 400
    if data.get('action') not in ('check_in', 'check_out'):
        return jsonify(ok=False, msg=tmsg('msg.bad_action')), 400
    with _write_lock:
        ticket = db.session.get(ClockTicket, tid)
        if ticket:
            if ticket.employee_id != data.get('employee_id') or ticket.action != data['action']:
                return jsonify(ok=False, msg=tmsg('msg.request_conflict')), 409
        else:
            emp = Employee.query.filter_by(employee_id=data.get('employee_id'), is_active=True).first()
            if not emp:
                return jsonify(ok=False, msg=load_translations(get_lang())['error.employee_not_found']), 404
            ticket = ClockTicket(id=tid, employee_id=emp.employee_id, action=data['action'], day=today().isoformat())
            db.session.add(ticket)
            db.session.commit()
            _check_queue.put({'job_id': tid, 'data': data, 'lang': get_lang(), 'ticket': True})
    _ensure_check_worker()
    return jsonify(ok=True, request_id=tid), 202

@app.route('/api/clock/tickets/<tid>')
def get_clock_ticket(tid):
    emp = clock_identity()
    if not emp:
        return schedule_error('expired', 401)
    from models import ClockTicket
    ticket = db.session.get(ClockTicket, tid)
    if not ticket:
        return jsonify(ok=False, missing=True), 404
    if ticket.employee_id != emp.employee_id:
        return schedule_error('own_only', 403)
    if ticket.result:
        return jsonify(pending=False, result=json.loads(ticket.result))
    if ticket.process_id == CLOCK_PROCESS_ID:
        return jsonify(pending=True)
    # A process may stop after committing the attendance record but before the ticket.
    emp = Employee.query.filter_by(employee_id=ticket.employee_id).first()
    record = AttendanceRecord.query.filter_by(employee_id=emp.id, date=date.fromisoformat(ticket.day)).first() if emp else None
    recorded = getattr(record, ticket.action, None) if record else None
    if recorded and recorded >= ticket.created_at:
        return jsonify(pending=False, result={'ok': True, 'msg': tmsg('msg.recorded'), 'time': recorded.strftime('%H:%M:%S')})
    if ticket.process_id != CLOCK_PROCESS_ID:
        return jsonify(pending=False, result={'ok': False, 'msg': tmsg('msg.restarted')})
    return jsonify(pending=True)


@app.route('/')
def index():
    config = clock_theme_config()
    emp = clock_identity(page=True)
    if not emp:
        return redirect(url_for('clock_access_page', lang=get_lang()))
    return render_clock(config['theme'], [emp], config, False)


@app.route('/api/check', methods=['POST'])
def api_check():
    """Clock in or out — queued for orderly processing."""
    emp = clock_identity()
    if not emp:
        return schedule_error('expired', 401)
    data = request.get_json(silent=True) or {}
    if data.get('employee_id') != emp.employee_id:
        return schedule_error('own_only', 403)
    lang = get_lang()
    job_id = str(uuid.uuid4())

    # Pre-validate: employee exists
    eid = data.get('employee_id')
    emp = Employee.query.filter_by(employee_id=eid, is_active=True).first()
    if not emp:
        t = load_translations(lang)
        return jsonify({'ok': False, 'msg': t['error.employee_not_found']}), 404

    _check_queue.put({'job_id': job_id, 'data': data, 'lang': lang})
    _ensure_check_worker()

    # Poll for result (up to ~15s)
    deadline = time_module.time() + 15
    while time_module.time() < deadline:
        with _check_results_lock:
            if job_id in _check_results:
                result = _check_results.pop(job_id)
                status_code = 200 if result.get('ok') else (result.get('_code', 400))
                return jsonify(result), status_code
        time_module.sleep(0.05)

    return jsonify({'ok': False, 'msg': tmsg('msg.queue_timeout')}), 503


@app.route('/api/check/queue')
def api_check_queue_status():
    """Return current queue depth (for debugging/monitoring)."""
    return jsonify({
        'ok': True,
        'queue_depth': _check_queue.qsize(),
    })


@app.route('/api/today/<employee_id>')
def api_today(employee_id):
    """Get only the verified employee's status."""
    emp = clock_identity()
    if not emp:
        return schedule_error('expired', 401)
    if emp.employee_id != employee_id:
        return schedule_error('own_only', 403)

    dt_today = today()
    now = now_dt()
    book = ShiftBook([emp.id], dt_today - timedelta(days=1), dt_today)
    record, record_day = current_record(emp, now, dt_today, book)
    shift = book.shift(emp, record_day)

    result = {
        'ok': True,
        'name': emp.name,
        'department': emp.department,
        'check_in': record.check_in.strftime('%H:%M:%S') if record and record.check_in else None,
        'check_out': record.check_out.strftime('%H:%M:%S') if record and record.check_out else None,
        'status': record.status if record else None,
        # is_off 只是提示「今天没有排班」，不再阻止打卡。
        'is_off': shift is None,
        'overnight': record_day != dt_today,
    }
    if shift:
        result['schedule'] = {
            'start': shift['start'],
            'end': shift['end'],
            'end_ts': int(shift['end_dt'].timestamp() * 1000),
        }

    return jsonify(result)


@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang not in ('zh', 'en', 'ja'):
        return redirect(request.referrer or url_for('index'))
    session['lang'] = lang

    # Keep the selected language in the URL as well as the session.  This
    # matters when the referrer already contains ?lang=zh: redirecting back
    # unchanged would immediately override the newly selected language.
    referrer = request.referrer
    if referrer:
        parts = urllib.parse.urlsplit(referrer)
        if parts.netloc and parts.netloc != request.host:
            target = url_for('index', lang=lang)
        else:
            query = [(key, value) for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
                     if key != 'lang']
            query.append(('lang', lang))
            target = urllib.parse.urlunsplit(('', '', parts.path or '/', urllib.parse.urlencode(query), parts.fragment))
    else:
        target = url_for('index', lang=lang)
    return redirect(target)


# ── QR Code Routes ────────────────────────────────────────────────

def clock_entry_url():
    """员工扫码进入的地址（不含语言参数，用于判断二维码是否仍然有效）。"""
    port = request.host.split(':')[-1] if ':' in request.host else str(SERVER_PORT)
    return f'http://{get_lan_ip()}:{port}/clock/access'


def remember_qr_url():
    """记住最近一次展示或打印的二维码地址，地址变化时在后台首页提醒。"""
    url = clock_entry_url()
    if Setting.get('qr_last_url') != url:
        Setting.set('qr_last_url', url)


@app.route('/api/server-info')
def api_server_info():
    """Return LAN IP and port for QR code generation."""
    port = request.host.split(':')[-1] if ':' in request.host else str(SERVER_PORT)
    if request.args.get('remember'):
        remember_qr_url()
    return jsonify({
        'ok': True,
        'app': 'attendance-system',
        'version': APP_VERSION,
        'ip': get_lan_ip(),
        'port': port,
        'url': f'{clock_entry_url()}?lang={get_lang()}',
    })


@app.route('/api/qrcode')
def api_qrcode():
    """Generate a QR code SVG for the given URL."""
    import qrcode
    import qrcode.image.svg

    url = request.args.get('url', '')
    if not url:
        return jsonify({'ok': False, 'msg': 'Missing url param'}), 400

    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=10)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode('utf-8')

    return svg, 200, {'Content-Type': 'image/svg+xml'}


@app.route('/api/qrcode/print')
def qrcode_print():
    """Print-optimized QR code page for download/save-as-PDF."""
    import qrcode
    import qrcode.image.svg

    url = f'{clock_entry_url()}?lang={get_lang()}'
    remember_qr_url()

    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=12)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode('utf-8')

    title, hint, print_label = tmsg('qr.title'), tmsg('qr.hint'), tmsg('qr.print')
    return f'''<!DOCTYPE html>
<html lang="{get_lang()}">
<head>
<meta charset="utf-8">
<title>{html_escape(title)}</title>
<style>
* {{ margin:0;padding:0;box-sizing:border-box; }}
body {{ font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#fff; }}
.qr-page {{ text-align:center;padding:40px; }}
h1 {{ font-size:24px;margin-bottom:8px;color:#1a202c; }}
.url {{ font-size:14px;color:#64748b;margin-bottom:32px;word-break:break-all; }}
.qr-wrap {{ display:inline-block;padding:24px;background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,0.1); }}
.qr-wrap svg {{ display:block;width:280px;height:280px; }}
.hint {{ margin-top:24px;font-size:13px;color:#94a3b8; }}
@media print {{ .no-print {{ display:none; }} }}
</style>
</head>
<body>
<div class="qr-page">
<h1>📱 {html_escape(title)}</h1>
<div class="url">{url}</div>
<div class="qr-wrap">{svg}</div>
<div class="hint">{html_escape(hint)}</div>
<div class="no-print" style="margin-top:32px;">
<button onclick="window.print()" style="padding:12px 32px;font-size:16px;border:none;border-radius:10px;background:#3b82f6;color:white;cursor:pointer;font-weight:600;">🖨️ {html_escape(print_label)}</button>
</div>
</div>
<script>setTimeout(()=>window.print(),300)</script>
</body>
</html>''', 200, {'Content-Type': 'text/html'}


# ── Routes: Admin ─────────────────────────────────────────────────

@app.route('/admin/')
def admin_index():
    return render_template('admin.html')


@app.route('/api/dashboard/today')
def api_dashboard_today():
    """后台首页：今天谁到了、谁没到，昨天谁忘了签退。"""
    day = today()
    now = now_dt()
    yesterday = day - timedelta(days=1)
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    rows = attendance_rows(employees, yesterday, day, now)
    today_rows = [row for row in rows if row['date'] == day.isoformat()]
    attention = [row for row in rows
                 if row['date'] == yesterday.isoformat() and row['status'] in ('partial', 'absent')]
    saved_url = Setting.get('qr_last_url')
    latest_backup = backup_module.last_backup_time()
    return jsonify(
        ok=True,
        date=day.isoformat(),
        employee_count=len(employees),
        rows=today_rows,
        attention=attention,
        qr_changed=bool(saved_url) and saved_url != clock_entry_url(),
        last_backup=latest_backup.strftime('%Y-%m-%d %H:%M') if latest_backup else '',
    )


@app.route('/api/backup/download')
def api_backup_download():
    """立即生成一份数据备份并下载。"""
    path = backup_module.make_backup('manual')
    if not path:
        return jsonify(ok=False, msg=tmsg('backup.failed')), 500
    return send_file(str(path), as_attachment=True, download_name=path.name,
                     mimetype='application/octet-stream')


@app.route('/admin/employees')
def admin_employees():
    employees = Employee.query.order_by(Employee.is_active.desc(), Employee.name).all()
    return render_template('admin_employees.html', employees=employees, rules=get_rules())


def next_employee_id():
    used = {row[0] for row in db.session.query(Employee.employee_id).all()}
    number = len(used) + 1
    while f'E{number:03d}' in used:
        number += 1
    return f'E{number:03d}'


@app.route('/api/employee', methods=['POST'])
def api_add_employee():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name') or '').strip()
    if not name:
        return jsonify(ok=False, msg=tmsg('admin.name_required')), 400
    employment_type = data.get('employment_type', 'regular' if '全职' in (data.get('department', '') or '') else 'part_time')
    if employment_type not in ('regular', 'part_time'):
        return jsonify(ok=False, msg=load_translations(get_lang())['admin.invalid_employment_type']), 400
    is_fulltime = employment_type == 'regular'
    try:
        min_rest = int(data.get('min_rest_per_week', 2 if is_fulltime else 0))
    except (TypeError, ValueError):
        min_rest = 2 if is_fulltime else 0
    with _write_lock:
        employee_id = str(data.get('employee_id') or '').strip()[:20] or next_employee_id()
        if Employee.query.filter_by(employee_id=employee_id).first():
            return jsonify(ok=False, msg=tmsg('admin.duplicate_id', employee_id=employee_id)), 409
        emp = Employee(
            employment_type=employment_type,
            employee_id=employee_id,
            name=name[:100],
            department=str(data.get('department') or '')[:100],
            lang=data.get('lang', 'zh'),
            rest_days=data.get('rest_days', '5,6' if is_fulltime else ''),
            min_rest_per_week=min_rest,
        )
        db.session.add(emp)
        db.session.flush()
        if is_fulltime:
            # 正式员工默认周一到周五上班；兼职按排班结果或实际打卡计。
            rules = get_rules()
            for dow in range(5):
                db.session.add(Schedule(
                    employee_id=emp.id, day_of_week=dow,
                    start_time=rules['work_start'], end_time=rules['work_end'],
                    is_off=False,
                ))
        with _schedule_access_lock:
            code = issue_code(emp.id)
        db.session.commit()
    return jsonify({'ok': True, 'id': emp.id, 'employee_id': emp.employee_id, 'code': code})


@app.route('/api/employee/<int:eid>', methods=['PUT'])
def api_update_employee(eid):
    data = request.get_json(silent=True) or {}
    emp = Employee.query.get_or_404(eid)
    employment_type = data.get('employment_type', emp.employment_type)
    if employment_type not in ('regular', 'part_time'):
        return jsonify(ok=False, msg=load_translations(get_lang())['admin.invalid_employment_type']), 400
    name = str(data.get('name', emp.name) or '').strip()
    if not name:
        return jsonify(ok=False, msg=tmsg('admin.name_required')), 400
    emp.employment_type = employment_type
    emp.name = name[:100]
    emp.department = str(data.get('department', emp.department) or '')[:100]
    emp.lang = data.get('lang', emp.lang)
    emp.is_active = bool(data.get('is_active', emp.is_active))
    emp.rest_days = data.get('rest_days', emp.rest_days)
    try:
        emp.min_rest_per_week = int(data.get('min_rest_per_week', emp.min_rest_per_week or 0))
    except (TypeError, ValueError):
        pass
    if not emp.is_active:
        # 离职后立即退出其正在使用的打卡和报班页面；考勤记录全部保留。
        ScheduleSession.query.filter_by(employee_id=eid).delete(synchronize_session=False)
        ClockSession.query.filter_by(employee_id=eid).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/employee/<int:eid>', methods=['DELETE'])
def api_delete_employee(eid):
    """只允许删除没有任何考勤记录的员工（例如建错的）。有记录的请设为离职。"""
    emp = Employee.query.get_or_404(eid)
    if AttendanceRecord.query.filter_by(employee_id=eid).count():
        return jsonify(ok=False, msg=tmsg('admin.delete_has_records')), 409
    try:
        backup_module.make_backup('before-delete')
        ScheduleSession.query.filter_by(employee_id=eid).delete(synchronize_session=False)
        ClockSession.query.filter_by(employee_id=eid).delete(synchronize_session=False)
        ScheduleAccess.query.filter_by(employee_id=eid).delete(synchronize_session=False)
        SchedulePreference.query.filter_by(employee_id=eid).delete(synchronize_session=False)
        ScheduleAssignment.query.filter_by(employee_id=eid).delete(synchronize_session=False)
        Schedule.query.filter_by(employee_id=eid).delete(synchronize_session=False)
        db.session.delete(emp)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception:
        db.session.rollback()
        logger.exception('删除员工失败: %s', eid)
        return jsonify({'ok': False, 'msg': load_translations(get_lang())['admin.delete_failed']}), 500


@app.route('/api/employee/<int:eid>/schedules', methods=['GET', 'POST'])
def api_schedules(eid):
    """每周固定班次：周几上班、几点到几点。"""
    Employee.query.get_or_404(eid)
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        rows = {}
        try:
            for item in data.get('schedules', []):
                dow = int(item['day_of_week'])
                if not 0 <= dow <= 6:
                    raise ValueError('day_of_week')
                start = dtparser.parse(item.get('start_time') or '09:00').strftime('%H:%M')
                end = dtparser.parse(item.get('end_time') or '18:00').strftime('%H:%M')
                rows[dow] = (start, end, bool(item.get('is_off', False)))
        except (KeyError, TypeError, ValueError, OverflowError):
            return jsonify(ok=False, msg=tmsg('admin.save_failed')), 400
        with _write_lock:
            Schedule.query.filter_by(employee_id=eid).delete()
            for dow, (start, end, is_off) in sorted(rows.items()):
                db.session.add(Schedule(employee_id=eid, day_of_week=dow,
                                        start_time=start, end_time=end, is_off=is_off))
            db.session.commit()
        return jsonify({'ok': True})

    # GET
    schedules = Schedule.query.filter_by(employee_id=eid).order_by(Schedule.day_of_week).all()
    return jsonify([{
        'day_of_week': s.day_of_week,
        'start_time': s.start_time,
        'end_time': s.end_time,
        'is_off': s.is_off,
    } for s in schedules])


# ── Routes: Settings ──────────────────────────────────────────────

@app.route('/admin/settings')
def admin_settings():
    return render_template('admin_settings.html')


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """迟到邮件提醒的发件配置。"""
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        for key in SMTP_SETTING_KEYS:
            if key in data:
                Setting.set(key, str(data[key]))
        return jsonify({'ok': True})
    # GET
    settings = {key: Setting.get(key) for key in SMTP_SETTING_KEYS}
    return jsonify(settings)


@app.route('/api/rules', methods=['GET', 'POST'])
def api_rules():
    """考勤规则：默认上下班时间、午休、迟到宽限。"""
    if request.method == 'POST':
        try:
            cleaned = clean_rules(request.get_json(silent=True) or {})
        except (TypeError, ValueError):
            return jsonify(ok=False, msg=tmsg('rules.invalid')), 400
        for key, value in cleaned.items():
            Setting.set(key, value)
    return jsonify(ok=True, rules=get_rules())


# ── Routes: Admin — Attendance Record Edit ────────────────────────────

@app.route('/admin/attendance')
def admin_attendance():
    employees = Employee.query.order_by(Employee.is_active.desc(), Employee.name).all()
    return render_template('admin_attendance.html', employees=employees)


def _clock_text(moment, day):
    """打卡时间文本；跨到第二天的签退加上 (+1)。"""
    if not moment:
        return ''
    text = moment.strftime('%H:%M:%S')
    return text + ' (+1)' if moment.date() > day else text


def attendance_rows(employees, start, end, now=None):
    """指定员工在一段日期内的逐日考勤结论。

    只返回需要显示的日子：有打卡或请假的，以及应出勤但没来的。
    休息日没打卡、还没到的日子、离职员工的空白日都不出现。
    """
    now = now or now_dt()
    employees = list(employees)
    ids = [emp.id for emp in employees]
    book = ShiftBook(ids, start, end)
    records = {}
    if ids:
        for record in AttendanceRecord.query.filter(
            AttendanceRecord.employee_id.in_(ids),
            AttendanceRecord.date >= start,
            AttendanceRecord.date <= end,
        ).all():
            records[(record.employee_id, record.date)] = record

    rows = []
    for emp in employees:
        day = start
        while day <= end:
            record = records.get((emp.id, day))
            has_fact = record is not None and (record.check_in or record.status == 'leave')
            if has_fact or emp.is_active:
                shift = book.shift(emp, day)
                outcome = evaluate(record, shift, book.rules, now, day)
                if outcome['status'] is not None:
                    rows.append({
                        'date': day.isoformat(),
                        'name': emp.name,
                        'department': emp.department,
                        'employee_id': emp.employee_id,
                        'employment_type': emp.employment_type,
                        'check_in': _clock_text(record.check_in, day) if record else '',
                        'check_out': _clock_text(record.check_out, day) if record else '',
                        'status': outcome['status'],
                        'late': outcome['late'],
                        'working_hours': outcome['hours'],
                        'scheduled': shift is not None,
                        'shift': f"{shift['start']}–{shift['end']}" if shift else '',
                    })
            day += timedelta(days=1)
    return rows


@app.route('/api/attendance/records', methods=['POST'])
def api_attendance_records():
    """Fetch attendance records for a date range."""
    data = request.get_json(silent=True) or {}
    try:
        start = dtparser.parse(data['start_date']).date()
        end = dtparser.parse(data['end_date']).date()
    except (KeyError, TypeError, ValueError, OverflowError):
        return jsonify(ok=False, msg=tmsg('stats.bad_range')), 400

    emp = Employee.query.filter_by(employee_id=data.get('employee_id')).first()
    if not emp:
        return jsonify({'ok': False, 'msg': tmsg('error.employee_not_found')}), 404

    records = AttendanceRecord.query.filter(
        AttendanceRecord.employee_id == emp.id,
        AttendanceRecord.date >= start,
        AttendanceRecord.date <= end,
    ).order_by(AttendanceRecord.date.desc()).all()
    now = now_dt()
    book = ShiftBook([emp.id], start, end)
    result = []
    for r in records:
        outcome = evaluate(r, book.shift(emp, r.date), book.rules, now, r.date)
        result.append({
            'id': r.id,
            'date': r.date.isoformat(),
            'check_in': r.check_in.strftime('%H:%M:%S') if r.check_in else None,
            'check_out': r.check_out.strftime('%H:%M:%S') if r.check_out else None,
            'status': outcome['status'] or '',
        })
    return jsonify({'ok': True, 'records': result})


@app.route('/api/attendance/update', methods=['POST'])
def api_attendance_update():
    """Create or update a single attendance record."""
    data = request.get_json(silent=True) or {}
    try:
        record_date = dtparser.parse(data['date']).date()
        check_in = check_out = None
        if data.get('check_in'):
            check_in = datetime.combine(record_date, dtparser.parse(data['check_in']).time())
        if data.get('check_out'):
            check_out = datetime.combine(record_date, dtparser.parse(data['check_out']).time())
    except (KeyError, TypeError, ValueError, OverflowError):
        return jsonify(ok=False, msg=tmsg('stats.bad_range')), 400
    if check_out and not check_in:
        return jsonify(ok=False, msg=tmsg('msg.check_in_first')), 400
    if check_in and check_out and check_out <= check_in:
        check_out += timedelta(days=1)  # 签退早于签到：按跨夜班处理

    # 与打卡队列共用写入锁，避免补卡和员工打卡同时改同一条记录。
    with _write_lock:
        emp = Employee.query.filter_by(employee_id=data.get('employee_id')).first()
        if not emp:
            return jsonify({'ok': False, 'msg': tmsg('error.employee_not_found')}), 404

        record = AttendanceRecord.query.filter_by(
            employee_id=emp.id, date=record_date
        ).first()
        if not record:
            record = AttendanceRecord(employee_id=emp.id, date=record_date)
            db.session.add(record)

        if data.get('is_leave', False):
            # Mark as leave: clear check-in/out, no hours calculation
            record.check_in = None
            record.check_out = None
            record.working_hours = None
            record.status = 'leave'
        else:
            record.check_in = check_in
            record.check_out = check_out
            record.status = 'normal'
            book = ShiftBook([emp.id], record_date, record_date)
            outcome = apply_outcome(record, emp, record_date, book, now_dt())
            if not check_in:
                record.status = outcome['status'] or 'absent'

        db.session.commit()
    return jsonify({'ok': True, 'msg': tmsg('msg.saved')})


# ── Routes: Stats ─────────────────────────────────────────────────

@app.route('/admin/stats')
def admin_stats():
    employees = Employee.query.order_by(Employee.is_active.desc(), Employee.name).all()
    return render_template('admin_stats.html', employees=employees)


MAX_STATS_DAYS = 400


def stats_request():
    """解析统计请求，返回 (员工列表, 开始, 结束)；日期不合法时抛出 ValueError。"""
    data = request.get_json(silent=True) or {}
    start_str, end_str = data.get('start_date'), data.get('end_date')
    try:
        start = dtparser.parse(start_str).date() if start_str else today() - timedelta(days=30)
        end = dtparser.parse(end_str).date() if end_str else today()
    except (TypeError, OverflowError) as error:
        raise ValueError(str(error))
    if end < start or (end - start).days > MAX_STATS_DAYS:
        raise ValueError('range')

    employee_id = data.get('employee_id')
    if employee_id:
        employees = Employee.query.filter_by(employee_id=employee_id).all()
    else:
        # 在职员工，加上这段时间内有记录的离职员工（算工资仍然需要）。
        with_records = {row[0] for row in db.session.query(AttendanceRecord.employee_id).filter(
            AttendanceRecord.date >= start, AttendanceRecord.date <= end).distinct()}
        employees = [emp for emp in Employee.query.order_by(Employee.name).all()
                     if emp.is_active or emp.id in with_records]
    return employees, start, end


def summarize(rows):
    """把逐日结论汇总成出勤天数、工时和各类次数。"""
    summary = {'scheduled_days': 0, 'working_days': 0, 'total_hours': 0.0, 'late_count': 0,
               'early_count': 0, 'absent_count': 0, 'leave_count': 0, 'partial_count': 0}
    days_with_hours = 0
    check_in_minutes = []
    for row in rows:
        status = row['status']
        if row['scheduled'] and status != 'pending':
            summary['scheduled_days'] += 1
        if status == 'absent':
            summary['absent_count'] += 1
        elif status == 'leave':
            summary['leave_count'] += 1
        elif status == 'partial':
            summary['partial_count'] += 1
        if row['late']:
            summary['late_count'] += 1
        if status in ('early_leave', 'both'):
            summary['early_count'] += 1
        if row['check_in']:
            summary['working_days'] += 1
            hour, minute = row['check_in'].split(':')[:2]
            check_in_minutes.append(int(hour) * 60 + int(minute))
        if row['working_hours'] is not None:
            summary['total_hours'] += row['working_hours']
            days_with_hours += 1
    summary['total_hours'] = round(summary['total_hours'], 2)
    summary['avg_hours'] = round(summary['total_hours'] / days_with_hours, 2) if days_with_hours else 0
    summary['avg_check_in'] = ''
    if check_in_minutes:
        average = sum(check_in_minutes) / len(check_in_minutes)
        summary['avg_check_in'] = f'{int(average // 60):02d}:{int(average % 60):02d}'
    return summary


def per_employee_summary(employees, rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row['employee_id'], []).append(row)
    result = []
    for emp in employees:
        item = summarize(grouped.get(emp.employee_id, []))
        item.update(employee_id=emp.employee_id, name=emp.name, department=emp.department,
                    employment_type=emp.employment_type, is_active=emp.is_active)
        result.append(item)
    return result


@app.route('/api/stats', methods=['POST'])
def api_stats():
    try:
        employees, start, end = stats_request()
    except ValueError:
        return jsonify(ok=False, msg=tmsg('stats.bad_range')), 400
    return jsonify(attendance_rows(employees, start, end))


@app.route('/api/stats/summary', methods=['POST'])
def api_stats_summary():
    try:
        employees, start, end = stats_request()
    except ValueError:
        return jsonify(ok=False, msg=tmsg('stats.bad_range')), 400
    if not employees:
        return jsonify({'error': 'no employees'})
    return jsonify(summarize(attendance_rows(employees, start, end)))


@app.route('/api/stats/monthly', methods=['POST'])
def api_stats_monthly():
    """按人汇总：每人一行的出勤天数、总工时、迟到早退缺勤次数。"""
    try:
        employees, start, end = stats_request()
    except ValueError:
        return jsonify(ok=False, msg=tmsg('stats.bad_range')), 400
    rows = attendance_rows(employees, start, end)
    return jsonify(ok=True, employees=per_employee_summary(employees, rows))


@app.route('/api/stats/export', methods=['POST'])
def api_stats_export():
    """Export statistics as CSV: daily detail, or one row per employee (kind=summary)."""
    try:
        employees, start, end = stats_request()
    except ValueError:
        return jsonify(ok=False, msg=tmsg('stats.bad_range')), 400
    kind = (request.get_json(silent=True) or {}).get('kind', 'detail')

    t = load_translations(get_lang())
    status_labels = {key: t['status.' + key] for key in
                     ('normal', 'late', 'early_leave', 'both', 'absent', 'partial', 'working', 'pending')}
    status_labels['leave'] = t['stats.leave']
    type_labels = {'regular': t['admin.fulltime'], 'part_time': t['admin.parttime']}

    rows = attendance_rows(employees, start, end)
    output = io.StringIO()
    writer = csv.writer(output)

    if kind == 'summary':
        writer.writerow([t['admin.employee_id'], t['admin.name'], t['admin.department'], t['csv.type'],
                         t['stats.scheduled_days'], t['stats.working_days'], t['csv.hours'],
                         t['stats.late_count'], t['stats.early_count'], t['stats.absent'],
                         t['stats.leave'], t['stats.partial']])
        for item in per_employee_summary(employees, rows):
            writer.writerow([
                item['employee_id'], item['name'], item['department'],
                type_labels.get(item['employment_type'], ''),
                item['scheduled_days'], item['working_days'], f"{item['total_hours']:.2f}",
                item['late_count'], item['early_count'], item['absent_count'],
                item['leave_count'], item['partial_count'],
            ])
        filename = f'attendance_summary_{start.isoformat()}_{end.isoformat()}.csv'
    else:
        writer.writerow([t['csv.date'], t['admin.employee_id'], t['admin.name'], t['admin.department'], t['csv.type'],
                         t['stats.check_in'], t['stats.check_out'], t['stats.status'], t['csv.hours']])
        rows.sort(key=lambda x: (x['date'], x['employee_id']))
        for row in rows:
            is_regular = row['employment_type'] == 'regular'
            if is_regular:
                hours_display = t['csv.present'] if row['check_in'] else status_labels.get(row['status'], '-')
            elif row['working_hours'] is not None:
                # 保留两位小数，不再把 7.9 小时截成 7 小时。
                hours_display = f"{row['working_hours']:.2f}"
            else:
                hours_display = '-'
            writer.writerow([
                row['date'],
                row['employee_id'],
                row['name'],
                row['department'],
                type_labels.get(row['employment_type'], ''),
                row['check_in'],
                row['check_out'],
                status_labels.get(row['status'], row['status']),
                hours_display,
            ])
        filename = f'attendance_{start.isoformat()}_{end.isoformat()}.csv'

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv; charset=utf-8',
        as_attachment=True,
        download_name=filename,
    )


# ═══════════════════════════════════════════════════════════════
# ── Scheduling Routes ────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════

def next_month_range():
    """Return (first_day_of_next_month, last_day_of_next_month)."""
    t = today()
    first = date(t.year, t.month, 1)
    # move to next month
    if t.month == 12:
        first = date(t.year + 1, 1, 1)
    else:
        first = date(t.year, t.month + 1, 1)
    last = date(first.year, first.month, calendar.monthrange(first.year, first.month)[1])
    return first, last


@app.route('/schedule/')
def schedule_page():
    """Employee schedule preference page."""
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    first_day, last_day = next_month_range()
    return render_template('schedule.html', employees=employees,
                           first_day=first_day, last_day=last_day)


# A per-tab token prevents another tab's login from changing the active employee.
_schedule_access_lock = threading.Lock()
SCHEDULE_IDLE_SECONDS = 300


def schedule_error(key, status=400):
    return jsonify(ok=False, msg=load_translations(get_lang())['access.' + key]), status


def schedule_identity():
    token = request.headers.get('X-Schedule-Token', '')
    if not token:
        return None
    login = db.session.get(ScheduleSession, hashlib.sha256(token.encode()).hexdigest())
    if not login:
        return None
    emp = db.session.get(Employee, login.employee_id)
    if not emp or not emp.is_active or time_module.time() - login.last_active >= SCHEDULE_IDLE_SECONDS:
        db.session.delete(login)
        db.session.commit()
        return None
    login.last_active = time_module.time()
    db.session.commit()
    return emp


@app.after_request
def schedule_no_cache(response):
    if request.path == '/' or request.path.startswith(('/clock/access', '/api/clock/', '/api/today/', '/api/check', '/schedule/', '/api/schedule/access', '/api/schedule/preferences')) or request.path.endswith('/schedule-code'):
        response.headers['Cache-Control'] = 'no-store'
    return response


CODE_LENGTH = 4
CODE_SPACE = 10 ** CODE_LENGTH


def code_digest(code):
    """个人码的存储形式。

    四位码本身只有一万种，慢哈希并不能阻止穷举；这里用程序密钥做 HMAC，
    密钥与数据库分开存放，登录时也不必逐个员工做慢哈希。
    """
    key = str(app.config['SECRET_KEY']).encode('utf-8')
    return 'hmac$' + hmac.new(key, code.encode('utf-8'), hashlib.sha256).hexdigest()


def code_matches(stored, code):
    if stored.startswith('hmac$'):
        return hmac.compare_digest(stored, code_digest(code))
    try:
        return check_password_hash(stored, code)  # 旧版本发放的三位码
    except ValueError:
        return False


def valid_code_format(code):
    """新发放的码是四位；旧的三位码继续可用，直到管理员重置。"""
    return isinstance(code, str) and len(code) in (3, CODE_LENGTH) and all(c in '0123456789' for c in code)


def register_failure(row, now):
    """记一次输错。每连续错 5 次锁一会儿：1 分钟起，逐次加倍，最长 10 分钟。

    共用平板上有人手滑不会让全店等 10 分钟；持续乱猜的人会越等越久。
    """
    row.failures += 1
    if row.failures % 5 == 0:
        row.locked_until = now + min(600, 60 * 2 ** (row.failures // 5 - 1))
        return True
    return False


def issue_code(eid):
    """为员工生成新的四位个人码并返回。调用方负责加锁和提交。"""
    used = {row.code_hash for row in ScheduleAccess.query.all()}
    if len(used) >= CODE_SPACE:
        return None
    start = secrets.randbelow(CODE_SPACE)
    for offset in range(CODE_SPACE):
        code = f'{(start + offset) % CODE_SPACE:0{CODE_LENGTH}d}'
        # 只凭个人码识别身份，所以码不能重复，也不重复发回本人的旧码。
        if code_digest(code) not in used:
            break
    else:
        return None
    access = db.session.get(ScheduleAccess, eid)
    if not access:
        access = ScheduleAccess(employee_id=eid)
        db.session.add(access)
    access.code_hash = code_digest(code)
    access.failures = 0
    access.locked_until = 0
    ScheduleSession.query.filter_by(employee_id=eid).delete()
    ClockSession.query.filter_by(employee_id=eid).delete()
    return code


@app.route('/api/employee/<int:eid>/schedule-code', methods=['POST'])
def reset_schedule_code(eid):
    # Admin remains password-free by the owner's explicit choice; it is local-only.
    if not request.is_json:
        return schedule_error('failed')
    Employee.query.get_or_404(eid)
    with _schedule_access_lock:
        code = issue_code(eid)
        if code is None:
            return jsonify(ok=False, msg=load_translations(get_lang())['clock_access.capacity']), 409
        db.session.commit()
    return jsonify(ok=True, code=code)



def clock_identity(page=False):
    token = session.get('clock_token', '')
    if not token or (not page and request.headers.get('X-Clock-Token') != token):
        return None
    login = db.session.get(ClockSession, hashlib.sha256(token.encode()).hexdigest())
    if not login:
        return None
    emp = db.session.get(Employee, login.employee_id)
    if not emp or not emp.is_active or time_module.time() - login.last_active >= SCHEDULE_IDLE_SECONDS:
        db.session.delete(login)
        db.session.commit()
        return None
    # Background status polling must not keep an abandoned terminal signed in.
    return emp


@app.route('/clock/access')
def clock_access_page():
    old = session.pop('clock_token', '')
    if old:
        ClockSession.query.filter_by(token_hash=hashlib.sha256(old.encode()).hexdigest()).delete()
        db.session.commit()
    return render_template('clock_access.html')


@app.route('/api/clock/access/login', methods=['POST'])
def clock_login():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    if not valid_code_format(code):
        return schedule_error('three_digits')
    # Code-only entry cannot attribute wrong guesses to an employee; limit by source.
    address = hashlib.sha256((request.remote_addr or '').encode()).hexdigest()
    with _schedule_access_lock:
        attempt = db.session.get(ClockAccessAttempt, address)
        if not attempt:
            attempt = ClockAccessAttempt(address=address, failures=0, locked_until=0)
            db.session.add(attempt)
        now = time_module.time()
        if attempt.locked_until > now:
            return schedule_error('locked', 429)
        # 四位码直接比对；旧的三位码才需要逐个验证旧式哈希。
        legacy = len(code) != CODE_LENGTH
        matches = [(access, emp) for access, emp in db.session.query(ScheduleAccess, Employee).join(Employee, Employee.id == ScheduleAccess.employee_id).filter(Employee.is_active == True).all()
                   if access.code_hash.startswith('hmac$') != legacy and code_matches(access.code_hash, code)]
        if len(matches) != 1:
            locked = register_failure(attempt, now)
            db.session.commit()
            return schedule_error('locked' if locked else 'wrong', 429 if locked else 403)
        access, emp = matches[0]
        attempt.failures = 0
        attempt.locked_until = 0
        access.failures = 0
        access.locked_until = 0
        old = session.pop('clock_token', '')
        if old:
            ClockSession.query.filter_by(token_hash=hashlib.sha256(old.encode()).hexdigest()).delete()
        ClockSession.query.filter(ClockSession.last_active <= now - SCHEDULE_IDLE_SECONDS).delete()
        token = secrets.token_urlsafe(32)
        db.session.add(ClockSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), employee_id=emp.id, last_active=now))
        db.session.commit()
        session['clock_token'] = token
        return jsonify(ok=True)


@app.route('/api/clock/access/logout', methods=['POST'])
def clock_logout():
    token = session.get('clock_token', '')
    if request.headers.get('X-Clock-Token') != token:
        return schedule_error('expired', 401)
    ClockSession.query.filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).delete()
    session.pop('clock_token', None)
    db.session.commit()
    return jsonify(ok=True)


@app.route('/api/clock/access/keepalive', methods=['POST'])
def clock_keepalive():
    if not clock_identity():
        return schedule_error('expired', 401)
    login = db.session.get(ClockSession, hashlib.sha256(session['clock_token'].encode()).hexdigest())
    login.last_active = time_module.time()
    db.session.commit()
    return jsonify(ok=True)


@app.route('/api/schedule/access/login', methods=['POST'])
def schedule_login():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    if not valid_code_format(code):
        return schedule_error('three_digits')
    with _schedule_access_lock:
        emp = Employee.query.filter_by(employee_id=data.get('employee_id'), is_active=True).first()
        access = db.session.get(ScheduleAccess, emp.id) if emp else None
        if not access:
            return schedule_error('unissued', 403)
        now = time_module.time()
        if access.locked_until > now:
            return schedule_error('locked', 429)
        if not code_matches(access.code_hash, code):
            locked = register_failure(access, now)
            db.session.commit()
            return schedule_error('locked' if locked else 'wrong', 429 if locked else 403)
        access.failures = 0
        access.locked_until = 0
        ScheduleSession.query.filter(ScheduleSession.last_active <= now - SCHEDULE_IDLE_SECONDS).delete()
        token = secrets.token_urlsafe(32)
        db.session.add(ScheduleSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), employee_id=emp.id, last_active=now))
        db.session.commit()
        return jsonify(ok=True, token=token, name=emp.name)


@app.route('/api/schedule/access/logout', methods=['POST'])
def schedule_logout():
    token = request.headers.get('X-Schedule-Token', '')
    ScheduleSession.query.filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).delete()
    db.session.commit()
    return jsonify(ok=True)


@app.route('/api/schedule/access/keepalive', methods=['POST'])
def schedule_keepalive():
    return jsonify(ok=True) if schedule_identity() else schedule_error('expired', 401)


@app.route('/api/schedule/preferences/<employee_id>', methods=['GET'])
def api_get_preferences(employee_id):
    """Get preferences for an employee for next month."""
    emp = schedule_identity()
    if not emp:
        return schedule_error('expired', 401)
    if emp.employee_id != employee_id:
        return schedule_error('own_only', 403)

    first_day, last_day = next_month_range()
    prefs = SchedulePreference.query.filter(
        SchedulePreference.employee_id == emp.id,
        SchedulePreference.date >= first_day,
        SchedulePreference.date <= last_day,
    ).all()

    result = {}
    for p in prefs:
        result[p.date.isoformat()] = p.preference
    return jsonify({'ok': True, 'preferences': result, 'name': emp.name})


@app.route('/api/schedule/preferences', methods=['POST'])
def api_save_preferences():
    """Save multiple preferences at once."""
    data = request.get_json(silent=True) or {}
    emp = schedule_identity()
    if not emp:
        return schedule_error('expired', 401)
    if data.get('employee_id') != emp.employee_id:
        return schedule_error('own_only', 403)
    prefs = data.get('preferences', {})
    first, last = next_month_range()
    if not isinstance(prefs, dict) or not prefs:
        return schedule_error('failed')
    try:
        for day, pref in prefs.items():
            if not first <= date.fromisoformat(day) <= last or pref not in ('want_work', 'want_off', 'flexible'):
                return schedule_error('failed')
    except (TypeError, ValueError):
        return schedule_error('failed')

    try:
        for date_str, pref in prefs.items():
            dt_date = dtparser.parse(date_str).date()
            existing = SchedulePreference.query.filter_by(
                employee_id=emp.id, date=dt_date
            ).first()
            if existing:
                existing.preference = pref
            else:
                db.session.add(SchedulePreference(
                    employee_id=emp.id, date=dt_date, preference=pref
                ))
        token = request.headers.get('X-Schedule-Token', '')
        ScheduleSession.query.filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).delete()
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 500


@app.route('/admin/schedule')
def admin_schedule():
    """Admin scheduling page."""
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    first_day, last_day = next_month_range()
    return render_template('admin_scheduling.html', employees=employees,
                           first_day=first_day, last_day=last_day)


@app.route('/api/schedule/auto', methods=['POST'])
def api_auto_schedule():
    """Auto-generate schedule using heuristic algorithm."""
    data = request.get_json() or {}
    default_min = data.get('default_min', 5)
    # Per-day requirements: {'2026-07-01': 4, ...}
    specific_reqs = data.get('specific_days', {})

    def min_for_day(d):
        return specific_reqs.get(d.isoformat(), default_min)

    first_day, last_day = next_month_range()
    employees = Employee.query.filter_by(is_active=True).all()

    # Classify employees
    regulars = [e for e in employees if e.employment_type == 'regular']
    temps = [e for e in employees if e not in regulars]

    # Load all preferences for next month
    all_prefs = SchedulePreference.query.filter(
        SchedulePreference.date >= first_day,
        SchedulePreference.date <= last_day,
    ).all()
    pref_map = {}
    for p in all_prefs:
        pref_map.setdefault(p.employee_id, {})[p.date] = p.preference

        # ① 默认排班：未提交偏好的，沿用上月偏好；仍无则全职按周休二
    # 计算上个月范围
    last_first = date(first_day.year, first_day.month, 1) - timedelta(days=1)
    last_first = date(last_first.year, last_first.month, 1)
    last_last = date(first_day.year, first_day.month, 1) - timedelta(days=1)
    # 查询上月偏好
    last_prefs = SchedulePreference.query.filter(
        SchedulePreference.date >= last_first,
        SchedulePreference.date <= last_last,
    ).all()
    last_pref_map = {}
    for p in last_prefs:
        last_pref_map.setdefault(p.employee_id, {})[p.date] = p.preference

    for emp in employees:
        if emp.id in pref_map and pref_map[emp.id]:
            continue  # 已有提交，跳过
        # 没提交：尝试沿用上月
        used_last = False
        if emp.id in last_pref_map and last_pref_map[emp.id]:
            # 把上月同一天星期几的偏好复制到这个月
            d = first_day
            while d <= last_day:
                # 找上月同 weekday 最近的偏好
                target_wd = d.weekday()
                for ld, lp in last_pref_map[emp.id].items():
                    if ld.weekday() == target_wd:
                        pref_map.setdefault(emp.id, {})[d] = lp
                        used_last = True
                        break
                if emp.id not in pref_map or d not in pref_map[emp.id]:
                    # 上月没有对应天数的数据
                    if emp.employment_type == 'regular':
                        if d.weekday() < 5:
                            pref_map.setdefault(emp.id, {})[d] = 'want_work'
                        else:
                            pref_map.setdefault(emp.id, {})[d] = 'want_off'
                d += timedelta(days=1)
        elif emp.employment_type == 'regular':
            # 完全没数据 + 全职 → 默认周休二
            d = first_day
            while d <= last_day:
                if d.weekday() < 5:
                    pref_map.setdefault(emp.id, {})[d] = 'want_work'
                else:
                    pref_map.setdefault(emp.id, {})[d] = 'want_off'
                d += timedelta(days=1)    # Clear old assignments
    ScheduleAssignment.query.filter(
        ScheduleAssignment.date >= first_day,
        ScheduleAssignment.date <= last_day,
    ).delete()

    conflicts = []
    stats = {'total_days': 0, 'days_short': 0, 'total_shortage': 0}

    # Track consecutive work days per employee for max-5-day rule
    consec_work = {}  # emp.id -> count of consecutive work days so far

    # Process each day    # Process each day
    current = first_day
    while current <= last_day:
        stats['total_days'] += 1
        min_staff = min_for_day(current)

        assigned = set()

        # Formal employees take priority over part-time employees, regardless
        # of the latter's submitted work preference. Rest/continuous-work
        # constraints apply before either group is considered.
        eligible = [e for e in employees
                    if pref_map.get(e.id, {}).get(current) != 'want_off'
                    and consec_work.get(e.id, 0) < 5]
        regular_pool = [e for e in eligible if e.employment_type == 'regular']
        part_time_pool = [e for e in eligible if e.employment_type != 'regular']

        # Keep formal employees' requested/default working days even when
        # they exceed the minimum staffing requirement.
        assigned.update(e.id for e in regular_pool
                        if pref_map.get(e.id, {}).get(current) == 'want_work')
        for pool in (regular_pool, part_time_pool):
            candidates = [e for e in pool if e.id not in assigned]
            candidates.sort(key=lambda e: (
                0 if pref_map.get(e.id, {}).get(current) == 'want_work' else 1,
                random.random()))
            needed = max(0, min_staff - len(assigned))
            assigned.update(e.id for e in candidates[:needed])

        for emp in employees:
            consec_work[emp.id] = (consec_work.get(emp.id, 0) + 1
                                   if emp.id in assigned else 0)

        # Check for shortage
        if len(assigned) < min_staff:
            shortage = min_staff - len(assigned)
            stats['days_short'] += 1
            stats['total_shortage'] += shortage
            conflicts.append({
                'date': current.isoformat(),
                'weekday': tmsg('admin.day_%d' % current.weekday()),
                'assigned': len(assigned),
                'needed': min_staff,
                'shortage': shortage,
                'available_off': [e.name for e in employees
                                  if e.id not in assigned
                                  and pref_map.get(e.id, {}).get(current) == 'want_off'],
                'available_flex': [e.name for e in employees
                                   if e.id not in assigned
                                   and pref_map.get(e.id, {}).get(current) not in ('want_off', 'want_work')],
            })

        # Save assignments
        for emp in employees:
            note = ''
            pref = pref_map.get(emp.id, {}).get(current)
            if emp.id in assigned:
                if pref == 'want_off':
                    note = 'pref_off_assigned'
                elif pref == 'flexible':
                    note = 'flexible'
                elif not pref:
                    note = 'no_pref'
            else:
                if pref == 'want_work':
                    note = 'pref_work_adjusted'
                elif pref == 'want_off':
                    note = 'pref_off'

            db.session.add(ScheduleAssignment(
                employee_id=emp.id, date=current,
                is_working=emp.id in assigned,
                source='auto',
                note=note,
            ))

        current += timedelta(days=1)

    db.session.commit()

    return jsonify({
        'ok': True,
        'month': tmsg('msg.month_label', year=first_day.year, month=first_day.month),
        'stats': stats,
        'conflicts': conflicts[:10],
        'perfect': len(conflicts) == 0,
    })


@app.route('/api/schedule/result')
def api_schedule_result():
    """Get the generated schedule for next month."""
    first_day, last_day = next_month_range()
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()

    assignments = ScheduleAssignment.query.filter(
        ScheduleAssignment.date >= first_day,
        ScheduleAssignment.date <= last_day,
    ).order_by(ScheduleAssignment.date, ScheduleAssignment.employee_id).all()

    # Build a grid: date x employee
    days = []
    current = first_day
    while current <= last_day:
        days.append(current)
        current += timedelta(days=1)

    result = []
    assignment_map = {}
    day_counts = {}
    for a in assignments:
        assignment_map[(a.employee_id, a.date)] = a
        day_counts[a.date] = day_counts.get(a.date, 0) + (1 if a.is_working else 0)

    for emp in employees:
        emp_days = []
        for d in days:
            a = assignment_map.get((emp.id, d))
            if a:
                emp_days.append({
                    'date': d.isoformat(),
                    'weekday': d.weekday(),
                    'working': a.is_working,
                    'note': schedule_note_label(a.note or ''),
                })
            else:
                emp_days.append({
                    'date': d.isoformat(),
                    'weekday': d.weekday(),
                    'working': False,
                    'note': '',
                })
        result.append({
            'employee_id': emp.employee_id,
            'name': emp.name,
            'department': emp.department,
            'days': emp_days,
        })

    return jsonify({
        'ok': True,
        'first_day': first_day.isoformat(),
        'last_day': last_day.isoformat(),
        'employees': result,
        'day_counts': {d.isoformat(): day_counts.get(d, 0) for d in days},
    })


@app.route('/api/schedule/update', methods=['POST'])
def api_schedule_update():
    """Manual update to schedule assignments (swap or toggle)."""
    data = request.get_json()
    changes = data.get('changes', [])  # [{employee_id, date, is_working}]

    try:
        for ch in changes:
            emp = Employee.query.filter_by(employee_id=ch['employee_id']).first()
            if not emp:
                continue
            dt_date = dtparser.parse(ch['date']).date()
            a = ScheduleAssignment.query.filter_by(
                employee_id=emp.id, date=dt_date
            ).first()
            if a:
                a.is_working = ch['is_working']
                a.source = 'manual'
                a.note = ch.get('note', 'manual')
            else:
                db.session.add(ScheduleAssignment(
                    employee_id=emp.id, date=dt_date,
                    is_working=ch['is_working'],
                    source='manual',
                    note=ch.get('note', 'manual'),
                ))
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# ── Late Notification System ────────────────────────────────────
# ═══════════════════════════════════════════════════════════════

def send_late_email(emp_name, emp_id, department, scheduled_start,
                    smtp_server, smtp_port, smtp_user, smtp_password,
                    admin_email, email_from):
    """Send email notification about late check-in."""
    if not smtp_server or not admin_email:
        return  # SMTP not configured

    now_str = datetime.now().strftime('%H:%M')
    # Background job without a browser language: include Chinese, Japanese and English.
    parts = []
    for lang in ('zh', 'ja', 'en'):
        parts.append(tmsg('email.late_body', lang, name=emp_name, emp_id=emp_id, department=department or '-',
                          start=scheduled_start, now=now_str))
    subject = ' / '.join(tmsg('email.late_subject', lang, name=emp_name) for lang in ('zh', 'ja', 'en'))
    body = '\n\n────────\n\n'.join(parts)

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = email_from
    msg['To'] = admin_email

    # SSL (port 465) vs STARTTLS (port 587/25)
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10) as server:
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            if smtp_port not in (25, 1025):
                try:
                    server.starttls()
                except:
                    pass
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
    logger.info('已发送迟到通知: %s (%s)', emp_name, emp_id)


def check_late_checkins():
    """Background check: find employees who haven't clocked in past their start time + notify delay."""
    with app.app_context():
        smtp_server = Setting.get('smtp_server')
        admin_email = Setting.get('admin_email')
        if not smtp_server or not admin_email:
            return

        smtp_port = int(Setting.get('smtp_port') or '587')
        smtp_user = Setting.get('smtp_user')
        smtp_password = Setting.get('smtp_password')
        email_from = Setting.get('email_from') or smtp_user
        notify_min = int(Setting.get('late_notify_minutes') or '10')

        today_date = date.today()
        now = datetime.now()

        employees = Employee.query.filter_by(is_active=True).all()
        book = ShiftBook([emp.id for emp in employees], today_date, today_date)
        for emp in employees:
            shift = book.shift(emp, today_date)
            if not shift:
                continue

            # Only check if current time is past the notify threshold
            if now < shift['start_dt'] + timedelta(minutes=notify_min):
                continue

            record = AttendanceRecord.query.filter_by(
                employee_id=emp.id, date=today_date
            ).first()

            if record and (record.check_in or record.status == 'leave'):
                continue  # already checked in, or on leave

            if record and record.late_notified:
                continue  # already notified

            # Send notification and mark
            send_late_email(emp.name, emp.employee_id, emp.department,
                           shift['start'],
                           smtp_server, smtp_port, smtp_user, smtp_password,
                           admin_email, email_from)
            if not record:
                # 只是「已提醒」的标记，不代表到岗；状态不能留默认的 normal。
                record = AttendanceRecord(employee_id=emp.id, date=today_date, status='absent')
                db.session.add(record)
            record.late_notified = True
            db.session.commit()


def start_background_jobs():
    """后台线程：每分钟检查迟到提醒，并保证每天有一份自动备份。"""
    interval = app.config['LATE_CHECK_INTERVAL']

    def loop():
        while True:
            try:
                if backup_module.backup_if_due():
                    logger.info('已完成今日自动备份')
            except Exception:
                logger.exception('自动备份失败')
            try:
                check_late_checkins()
            except Exception:
                logger.exception('迟到检查失败')
            time_module.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    logger.info('后台任务已启动，间隔 %s 秒', interval)


def port_is_free(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(('0.0.0.0', port))
        return True
    except OSError:
        return False


def preferred_port():
    """上次使用的端口优先，保证已经打印的二维码继续有效。"""
    configured = os.environ.get('ATTENDANCE_PORT')
    if not configured:
        with app.app_context():
            configured = Setting.get('server_port')
    try:
        port = int(configured)
        return port if 1024 <= port <= 65535 else DEFAULT_PORT
    except (TypeError, ValueError):
        return DEFAULT_PORT


def choose_port(preferred):
    """首选端口被其他程序占用时（例如 macOS 的隔空播放占用 5000），自动换一个。"""
    for port in [preferred] + [p for p in range(DEFAULT_PORT, DEFAULT_PORT + 21) if p != preferred]:
        if port_is_free(port):
            return port
    return preferred


def open_browser(port):
    """延迟打开浏览器。"""
    def _open():
        time_module.sleep(1.5)
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{port}')
    threading.Thread(target=_open, daemon=True).start()


def existing_instance_is_running(port):
    """判断该端口上是否已经运行本系统。"""
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/server-info', timeout=1) as response:
            info = json.loads(response.read().decode('utf-8'))
            return response.status == 200 and bool(info.get('ok')) and 'url' in info
    except Exception:
        return False


if __name__ == '__main__':
    preferred = preferred_port()
    if existing_instance_is_running(preferred):
        for lang in ('zh', 'ja', 'en'):
            logger.info(tmsg('console.already_running', lang))
        open_browser(preferred)
        raise SystemExit(0)

    from waitress import serve

    SERVER_PORT = choose_port(preferred)
    with app.app_context():
        if Setting.get('server_port') != str(SERVER_PORT):
            Setting.set('server_port', str(SERVER_PORT))
    if SERVER_PORT != preferred:
        for lang in ('zh', 'ja', 'en'):
            logger.warning(tmsg('console.port_changed', lang, old=preferred, new=SERVER_PORT))

    open_browser(SERVER_PORT)
    start_background_jobs()
    # The console window is what non-technical users see: show it in all three languages.
    for lang in ('zh', 'ja', 'en'):
        logger.info(tmsg('console.started', lang, app=APP_NAME, version=APP_VERSION))
        logger.info(tmsg('console.local', lang, url=f'http://127.0.0.1:{SERVER_PORT}'))
        logger.info(tmsg('console.phone', lang, url=f'http://{get_lan_ip()}:{SERVER_PORT}'))
        logger.info(tmsg('console.stop', lang))
    serve(app, host='0.0.0.0', port=SERVER_PORT, threads=8)
