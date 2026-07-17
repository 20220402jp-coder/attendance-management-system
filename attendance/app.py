import json
import os
import sys
import csv
import io
import socket
import calendar
import random
import smtplib
import uuid
import time as time_module
import threading
import queue as queue_module
from datetime import date, datetime, timedelta
from functools import lru_cache
from email.mime.text import MIMEText

from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, send_file)
from dateutil import parser as dtparser

from config import Config, BASE_DIR, DATA_DIR
from logging_config import setup_logging
from models import (db, Employee, Schedule, AttendanceRecord,
                    SchedulePreference, ScheduleAssignment, Setting,
                    get_schedule_for_day, compute_working_hours,
                    compute_status)

# ── App factory ───────────────────────────────────────────────────

logger = setup_logging(
    os.environ.get('ATTENDANCE_LOG_DIR', os.path.join(DATA_DIR, 'logs'))
)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


def first_run_setup():
    """创建空数据库和全部数据表。

    该操作可重复执行，不会添加示例员工或改动已有数据。
    """
    db_path = os.path.join(DATA_DIR, 'attendance.db')
    is_new_database = not os.path.exists(db_path)
    with app.app_context():
        db.create_all()
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
                    result = _process_check(job['data'], job.get('lang', 'zh'))
            with _check_results_lock:
                _check_results[job_id] = result
        except Exception as e:
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

def _process_check(data, lang):
    """Core check-in/out logic (runs in worker thread with app context)."""
    t = load_translations(lang)
    employee_id = data.get('employee_id')
    pin = data.get('pin', '')
    action = data.get('action', 'check_in')

    emp = Employee.query.filter_by(employee_id=employee_id, is_active=True).first()
    if not emp:
        return {'ok': False, 'msg': t['error.employee_not_found'], '_code': 404}

    if emp.pin_code and emp.pin_code != pin:
        return {'ok': False, 'msg': t['home.invalid_pin'], '_code': 403}

    dt_today = today()
    now = now_dt()

    record = AttendanceRecord.query.filter_by(
        employee_id=emp.id, date=dt_today
    ).first()

    if not record:
        record = AttendanceRecord(employee_id=emp.id, date=dt_today)
        db.session.add(record)

    try:
        if action == 'check_in':
            if record.check_in:
                return {'ok': False, 'msg': t['home.already_checked_in'], '_code': 400}
            record.check_in = now
        elif action == 'check_out':
            if not record.check_in:
                return {'ok': False, 'msg': '先签到才能签退', '_code': 400}
            if record.check_out:
                return {'ok': False, 'msg': t['home.already_checked_out'], '_code': 400}
            record.check_out = now

        schedule = get_schedule_for_day(emp.id, dt_today)
        if schedule and not schedule.is_off:
            record.working_hours = compute_working_hours(
                record.check_in, record.check_out,
                app.config['LUNCH_START'], app.config['LUNCH_END'],
            )
            status, _ = compute_status(
                record.check_in, record.check_out, schedule,
                app.config['GRACE_PERIOD'],
            )
            record.status = status

        db.session.commit()

        msg = t['home.check_in_success'] if action == 'check_in' else t['home.check_out_success']
        return {
            'ok': True,
            'msg': msg,
            'time': now.strftime('%H:%M:%S'),
            'check_in': record.check_in.strftime('%H:%M:%S') if record.check_in else None,
            'check_out': record.check_out.strftime('%H:%M:%S') if record.check_out else None,
        }
    except Exception as e:
        db.session.rollback()
        return {'ok': False, 'msg': str(e)}


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

@app.route('/')
def index():
    lang = get_lang()
    t = load_translations(lang)
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    return render_template('index.html', employees=employees)


@app.route('/api/check', methods=['POST'])
def api_check():
    """Clock in or out — queued for orderly processing."""
    data = request.get_json()
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

    return jsonify({'ok': False, 'msg': '打卡排队超时，请重试'}), 503


@app.route('/api/check/queue')
def api_check_queue_status():
    """Return current queue depth (for debugging/monitoring)."""
    return jsonify({
        'ok': True,
        'queue_depth': _check_queue.qsize(),
    })


@app.route('/api/today/<employee_id>')
def api_today(employee_id):
    """Get today's status for an employee."""
    emp = Employee.query.filter_by(employee_id=employee_id, is_active=True).first()
    if not emp:
        return jsonify({'ok': False}), 404

    dt_today = today()
    record = AttendanceRecord.query.filter_by(
        employee_id=emp.id, date=dt_today
    ).first()

    schedule = get_schedule_for_day(emp.id, dt_today)

    result = {
        'ok': True,
        'name': emp.name,
        'department': emp.department,
        'has_pin': bool(emp.pin_code),
        'check_in': record.check_in.strftime('%H:%M:%S') if record and record.check_in else None,
        'check_out': record.check_out.strftime('%H:%M:%S') if record and record.check_out else None,
        'status': record.status if record else None,
    }

    if schedule and not schedule.is_off:
        result['schedule'] = {
            'start': schedule.start_time,
            'end': schedule.end_time,
        }
        result['is_off'] = False
    else:
        result['is_off'] = True

    return jsonify(result)


@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in ('zh', 'en', 'ja'):
        session['lang'] = lang
    return redirect(request.referrer or '/')


# ── QR Code Routes ────────────────────────────────────────────────

@app.route('/api/server-info')
def api_server_info():
    """Return LAN IP and port for QR code generation."""
    port = request.host.split(':')[-1] if ':' in request.host else '5000'
    return jsonify({
        'ok': True,
        'ip': get_lan_ip(),
        'port': port,
        'url': f'http://{get_lan_ip()}:{port}/',
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

    port = request.host.split(':')[-1] if ':' in request.host else '5000'
    url = f'http://{get_lan_ip()}:{port}/'

    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=12)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode('utf-8')

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>打卡二维码</title>
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
<h1>📱 打卡二维码</h1>
<div class="url">{url}</div>
<div class="qr-wrap">{svg}</div>
<div class="hint">手机扫码打开打卡页面</div>
<div class="no-print" style="margin-top:32px;">
<button onclick="window.print()" style="padding:12px 32px;font-size:16px;border:none;border-radius:10px;background:#3b82f6;color:white;cursor:pointer;font-weight:600;">🖨️ 打印 / 另存为 PDF</button>
</div>
</div>
<script>setTimeout(()=>window.print(),300)</script>
</body>
</html>''', 200, {'Content-Type': 'text/html'}


# ── Routes: Admin ─────────────────────────────────────────────────

@app.route('/admin/')
def admin_index():
    return render_template('admin.html')


@app.route('/admin/employees')
def admin_employees():
    employees = Employee.query.order_by(Employee.name).all()
    return render_template('admin_employees.html', employees=employees)


@app.route('/api/employee', methods=['POST'])
def api_add_employee():
    data = request.get_json()
    is_fulltime = '全职' in (data.get('department', '') or '')
    rest_days = data.get('rest_days', '5,6' if is_fulltime else '')
    min_rest = int(data.get('min_rest_per_week', 2 if is_fulltime else 0))
    emp = Employee(
        employee_id=data['employee_id'],
        name=data['name'],
        department=data.get('department', ''),
        lang=data.get('lang', 'zh'),
        pin_code=data.get('pin_code', ''),
        rest_days=rest_days,
        min_rest_per_week=min_rest,
    )
    db.session.add(emp)
    db.session.flush()
    for dow in (5, 6):
        sched = Schedule(
            employee_id=emp.id,
            day_of_week=dow,
            start_time='09:00',
            end_time='18:00',
            is_off=False,
        )
        db.session.add(sched)
    db.session.commit()
    return jsonify({'ok': True, 'id': emp.id})


@app.route('/api/employee/<int:eid>', methods=['PUT'])
def api_update_employee(eid):
    data = request.get_json()
    emp = Employee.query.get_or_404(eid)
    emp.name = data.get('name', emp.name)
    emp.department = data.get('department', emp.department)
    emp.lang = data.get('lang', emp.lang)
    emp.pin_code = data.get('pin_code', emp.pin_code)
    emp.is_active = data.get('is_active', emp.is_active)
    emp.rest_days = data.get('rest_days', emp.rest_days)
    emp.min_rest_per_week = int(data.get('min_rest_per_week', emp.min_rest_per_week or 0))
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/employee/<int:eid>', methods=['DELETE'])
def api_delete_employee(eid):
    emp = Employee.query.get_or_404(eid)
    db.session.delete(emp)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/employee/<int:eid>/schedules', methods=['GET', 'POST'])
def api_schedules(eid):
    if request.method == 'POST':
        data = request.get_json()
        # Replace all schedules
        Schedule.query.filter_by(employee_id=eid).delete()
        for s in data.get('schedules', []):
            sched = Schedule(
                employee_id=eid,
                day_of_week=s['day_of_week'],
                start_time=s.get('start_time', '09:00'),
                end_time=s.get('end_time', '18:00'),
                is_off=s.get('is_off', False),
            )
            db.session.add(sched)
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


# ── Routes: Stats ─────────────────────────────────────────────────

@app.route('/admin/settings')
def admin_settings():
    return render_template('admin_settings.html')




@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'POST':
        data = request.get_json()
        for key, value in data.items():
            Setting.set(key, str(value))
        return jsonify({'ok': True})
    # GET
    keys = ['smtp_server', 'smtp_port', 'smtp_user', 'smtp_password',
            'admin_email', 'email_from', 'late_notify_minutes']
    settings = {k: Setting.get(k) for k in keys}
    return jsonify(settings)


# ── Routes: Admin — Attendance Record Edit ────────────────────────────

@app.route('/admin/attendance')
def admin_attendance():
    employees = Employee.query.order_by(Employee.name).all()
    return render_template('admin_attendance.html', employees=employees)


@app.route('/api/attendance/records', methods=['POST'])
def api_attendance_records():
    """Fetch attendance records for a date range."""
    data = request.get_json()
    employee_id = data.get('employee_id')
    start = dtparser.parse(data['start_date']).date()
    end = dtparser.parse(data['end_date']).date()

    emp = Employee.query.filter_by(employee_id=employee_id).first()
    if not emp:
        return jsonify({'ok': False, 'msg': '员工不存在'}), 404

    records = AttendanceRecord.query.filter(
        AttendanceRecord.employee_id == emp.id,
        AttendanceRecord.date >= start,
        AttendanceRecord.date <= end,
    ).order_by(AttendanceRecord.date.desc()).all()

    return jsonify({
        'ok': True,
        'records': [{
            'id': r.id,
            'date': r.date.isoformat(),
            'check_in': r.check_in.strftime('%H:%M:%S') if r.check_in else None,
            'check_out': r.check_out.strftime('%H:%M:%S') if r.check_out else None,
            'status': r.status or '',
        } for r in records],
    })


@app.route('/api/attendance/update', methods=['POST'])
def api_attendance_update():
    """Create or update a single attendance record."""
    with _write_lock:
        data = request.get_json()
    employee_id = data.get('employee_id')
    record_date = dtparser.parse(data['date']).date()

    emp = Employee.query.filter_by(employee_id=employee_id).first()
    if not emp:
        return jsonify({'ok': False, 'msg': '员工不存在'}), 404

    # Parse times
    check_in = None
    if data.get('check_in'):
        t = dtparser.parse(data['check_in']).time()
        check_in = datetime.combine(record_date, t)
    check_out = None
    if data.get('check_out'):
        t = dtparser.parse(data['check_out']).time()
        check_out = datetime.combine(record_date, t)

    # Find or create record
    record = AttendanceRecord.query.filter_by(
        employee_id=emp.id, date=record_date
    ).first()
    if not record:
        record = AttendanceRecord(employee_id=emp.id, date=record_date)
        db.session.add(record)

    # Handle leave marking
    is_leave = data.get('is_leave', False)
    record.check_in = check_in
    record.check_out = check_out

    if is_leave:
        # Mark as leave: clear check-in/out, no hours calculation
        record.check_in = None
        record.check_out = None
        record.working_hours = None
        record.status = 'leave'
    else:
        # Recompute status & hours
        schedule = get_schedule_for_day(emp.id, record_date)
        if schedule and not schedule.is_off:
            record.working_hours = compute_working_hours(
                record.check_in, record.check_out,
                app.config['LUNCH_START'], app.config['LUNCH_END'],
            )
            status, _ = compute_status(
                record.check_in, record.check_out, schedule,
                app.config['GRACE_PERIOD'],
            )
            record.status = status
        else:
            record.working_hours = None
            record.status = None

    db.session.commit()
    return jsonify({'ok': True, 'msg': '已保存'})


@app.route('/admin/stats')
def admin_stats():
    employees = Employee.query.order_by(Employee.name).all()
    return render_template('admin_stats.html', employees=employees)


def _fill_stats(records_by_eid, emp, start, end):
    """Fill in absent/leave records for work days without check-in."""
    rows = []
    existing = {r.date: r for r in records_by_eid.get(emp.id, [])}
    delta = (end - start).days
    for i in range(delta + 1):
        d = start + timedelta(days=i)
        schedule = get_schedule_for_day(emp.id, d)
        # Skip rest days (off per schedule)
        if schedule and schedule.is_off:
            continue
        if d in existing:
            r = existing[d]
            rows.append({
                'date': d.isoformat(),
                'name': emp.name,
                'department': emp.department,
                'employee_id': emp.employee_id,
                'check_in': r.check_in.strftime('%H:%M:%S') if r.check_in else '',
                'check_out': r.check_out.strftime('%H:%M:%S') if r.check_out else '',
                'status': 'leave' if r.status == 'leave' else (r.status or ''),
                'working_hours': r.working_hours,
            })
        else:
            # No record on a work day → absent
            rows.append({
                'date': d.isoformat(),
                'name': emp.name,
                'department': emp.department,
                'employee_id': emp.employee_id,
                'check_in': '',
                'check_out': '',
                'status': 'absent',
                'working_hours': None,
            })
    return rows


def api_stats():
    data = request.get_json()
    employee_id = data.get('employee_id')
    start_str = data.get('start_date')
    end_str = data.get('end_date')

    start = dtparser.parse(start_str).date() if start_str else today() - timedelta(days=30)
    end = dtparser.parse(end_str).date() if end_str else today()

    # Determine which employees to show
    if employee_id:
        emps = Employee.query.filter_by(employee_id=employee_id, is_active=True).all()
    else:
        emps = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()

    if not emps:
        return jsonify([])

    # Fetch all records for these employees in range
    emp_ids = [e.id for e in emps]
    all_records = AttendanceRecord.query.filter(
        AttendanceRecord.employee_id.in_(emp_ids),
        AttendanceRecord.date >= start,
        AttendanceRecord.date <= end,
    ).all()

    # Group records by employee_id
    records_by_eid = {}
    for r in all_records:
        records_by_eid.setdefault(r.employee_id, []).append(r)

    result = []
    for emp in emps:
        result.extend(_fill_stats(records_by_eid, emp, start, end))

    return jsonify(result)


@app.route('/api/stats', methods=['POST'])
def api_stats_wrapper():
    return api_stats()


@app.route('/api/stats/summary', methods=['POST'])
def api_stats_summary():
    data = request.get_json()
    employee_id = data.get('employee_id')
    start_str = data.get('start_date')
    end_str = data.get('end_date')

    start = dtparser.parse(start_str).date() if start_str else today() - timedelta(days=30)
    end = dtparser.parse(end_str).date() if end_str else today()

    if employee_id:
        emps = Employee.query.filter_by(employee_id=employee_id, is_active=True).all()
    else:
        emps = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()

    if not emps:
        return jsonify({'error': 'no employees'})

    emp_ids = [e.id for e in emps]
    all_records = AttendanceRecord.query.filter(
        AttendanceRecord.employee_id.in_(emp_ids),
        AttendanceRecord.date >= start,
        AttendanceRecord.date <= end,
    ).all()

    records_by_eid = {}
    for r in all_records:
        records_by_eid.setdefault(r.employee_id, []).append(r)

    total_scheduled = 0
    total_present = 0
    total_hours = 0.0
    late_count = 0
    early_count = 0
    check_in_times = []
    absent_count = 0
    leave_count = 0

    for emp in emps:
        rows = _fill_stats(records_by_eid, emp, start, end)
        for row in rows:
            total_scheduled += 1
            s = row['status']
            if s == 'absent':
                absent_count += 1
            elif s == 'leave':
                leave_count += 1
            elif s in ('late', 'both'):
                late_count += 1
            if s in ('early_leave', 'both'):
                early_count += 1
            if row['working_hours'] and s != 'absent' and s != 'leave':
                total_hours += row['working_hours']
                total_present += 1
            if row['check_in']:
                parts = row['check_in'].split(':')
                check_in_times.append(int(parts[0]) * 60 + int(parts[1]))

    avg_check_in = ''
    if check_in_times:
        avg_minutes = sum(check_in_times) / len(check_in_times)
        avg_check_in = f'{int(avg_minutes // 60):02d}:{int(avg_minutes % 60):02d}'

    return jsonify({
        'working_days': total_present,
        'scheduled_days': total_scheduled,
        'total_hours': round(total_hours, 2),
        'avg_hours': round(total_hours / total_present, 2) if total_present else 0,
        'late_count': late_count,
        'early_count': early_count,
        'absent_count': absent_count,
        'leave_count': leave_count,
        'avg_check_in': avg_check_in,
    })


@app.route('/api/stats/export', methods=['POST'])
def api_stats_export():
    """Export statistics as CSV."""
    data = request.get_json()
    start_str = data.get('start_date')
    end_str = data.get('end_date')

    start = dtparser.parse(start_str).date() if start_str else today() - timedelta(days=30)
    end = dtparser.parse(end_str).date() if end_str else today()

    STATUS_LABELS = {
        'normal': '正常',
        'late': '迟到',
        'early_leave': '早退',
        'both': '迟到+早退',
        'absent': '缺勤',
        'partial': '未签退',
        'leave': '请假',
    }

    employee_id = data.get('employee_id')
    if employee_id:
        emps = Employee.query.filter_by(employee_id=employee_id, is_active=True).all()
    else:
        emps = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    emp_ids = [e.id for e in emps]
    all_records = AttendanceRecord.query.filter(
        AttendanceRecord.employee_id.in_(emp_ids),
        AttendanceRecord.date >= start,
        AttendanceRecord.date <= end,
    ).all()

    records_by_eid = {}
    for r in all_records:
        records_by_eid.setdefault(r.employee_id, []).append(r)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['日期', '工号', '姓名', '部门', '类型', '签到', '签退', '状态', '工时/天数'])

    rows = []
    for emp in emps:
        rows.extend(_fill_stats(records_by_eid, emp, start, end))
    rows.sort(key=lambda x: (x['date'], x['employee_id']))

    for row in rows:
        emp_obj = Employee.query.filter_by(employee_id=row['employee_id']).first()
        is_regular = '全职' in (emp_obj.department or '') if emp_obj else False
        emp_type = '全职' if is_regular else '兼职'
        status = STATUS_LABELS.get(row['status'], row['status'])
        if is_regular:
            hours_display = '✓出勤' if row['check_in'] else ('请假' if row['status'] == 'leave' else '缺勤')
        else:
            if row['working_hours'] is not None:
                hours_display = str(int(row['working_hours'])) + 'h'
            else:
                hours_display = '-'
        
        writer.writerow([
            row['date'],
            row['employee_id'],
            row['name'],
            row['department'],
            emp_type,
            row['check_in'],
            row['check_out'],
            status,
            hours_display,
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv; charset=utf-8',
        as_attachment=True,
        download_name=f'attendance_{start.isoformat()}_{end.isoformat()}.csv',
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


@app.route('/api/schedule/preferences/<employee_id>', methods=['GET'])
def api_get_preferences(employee_id):
    """Get preferences for an employee for next month."""
    emp = Employee.query.filter_by(employee_id=employee_id, is_active=True).first()
    if not emp:
        return jsonify({'ok': False}), 404

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
    data = request.get_json()
    employee_id = data.get('employee_id')
    prefs = data.get('preferences', {})  # {'2026-07-01': 'want_work', ...}

    emp = Employee.query.filter_by(employee_id=employee_id, is_active=True).first()
    if not emp:
        return jsonify({'ok': False, 'msg': '员工不存在'}), 404

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
    regulars = [e for e in employees if '全职' in (e.department or '')]
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
                    if '全职' in (emp.department or ''):
                        if d.weekday() < 5:
                            pref_map.setdefault(emp.id, {})[d] = 'want_work'
                        else:
                            pref_map.setdefault(emp.id, {})[d] = 'want_off'
                d += timedelta(days=1)
        elif '全职' in (emp.department or ''):
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

        # Phase 1: Assign must-work people
        for emp in employees:
            pref = pref_map.get(emp.id, {}).get(current)
            if pref == 'want_work':
                assigned.add(emp.id)

        # Phase 2: Fill with flexible people — ② 全职优先 + ③ 最多连5天
        if len(assigned) < min_staff:
            # Build pool: exclude want_off and employees who already worked 5+ consecutive days
            flex_pool = []
            for e in employees:
                if e.id in assigned:
                    continue
                pref = pref_map.get(e.id, {}).get(current)
                if pref == 'want_off':
                    continue
                # Check consecutive work limit
                if consec_work.get(e.id, 0) >= 5:
                    continue
                flex_pool.append(e)
            # Full-time employees first
            flex_pool.sort(key=lambda e: (0 if '全职' in (e.department or '') else 1, random.random()))
            needed = min_staff - len(assigned)
            for emp in flex_pool[:needed]:
                assigned.add(emp.id)

        # Track consecutive work days
        for emp in employees:
            if emp.id in assigned:
                consec_work[emp.id] = consec_work.get(emp.id, 0) + 1
            else:
                consec_work[emp.id] = 0

        # Phase 3:        # Phase 3: Handle regular employees' 2-days-off requirement per week
        for emp in regulars:
            pref = pref_map.get(emp.id, {}).get(current)
            if pref == 'want_off' and emp.id in assigned:
                if len(assigned) - 1 >= min_staff:
                    assigned.remove(emp.id)

        # Check for shortage
        if len(assigned) < min_staff:
            shortage = min_staff - len(assigned)
            stats['days_short'] += 1
            stats['total_shortage'] += shortage
            conflicts.append({
                'date': current.isoformat(),
                'weekday': ['一','二','三','四','五','六','日'][current.weekday()],
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
                    note = '偏好休息但排班'
                elif pref == 'flexible':
                    note = '都可'
                elif not pref:
                    note = '未提交偏好'
            else:
                if pref == 'want_work':
                    note = '偏好上班但调整'
                elif pref == 'want_off':
                    note = '偏好休息'

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
        'month': f'{first_day.year}年{first_day.month}月',
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
                    'note': a.note or '',
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
                a.note = ch.get('note', '手动调整')
            else:
                db.session.add(ScheduleAssignment(
                    employee_id=emp.id, date=dt_date,
                    is_working=ch['is_working'],
                    source='manual',
                    note=ch.get('note', '手动调整'),
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
    subject = f'[考勤] {emp_name} 迟到通知'
    body = f'''{emp_name}（工号: {emp_id}，部门: {department}）今日迟到。

应到时间: {scheduled_start}
当前时间: {now_str}

此邮件由考勤系统自动发送。'''

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
        cfg = app.config
        # Read settings from DB (with env fallback)
        smtp_server = Setting.get('smtp_server') or cfg.get('SMTP_SERVER', '')
        smtp_port = int(Setting.get('smtp_port') or cfg.get('SMTP_PORT', '587'))
        smtp_user = Setting.get('smtp_user') or cfg.get('SMTP_USER', '')
        smtp_password = Setting.get('smtp_password') or cfg.get('SMTP_PASSWORD', '')
        admin_email = Setting.get('admin_email') or cfg.get('ADMIN_EMAIL', '')
        email_from = Setting.get('email_from') or cfg.get('EMAIL_FROM', 'attendance@local')
        notify_min = int(Setting.get('late_notify_minutes') or cfg.get('LATE_NOTIFY_MINUTES', '10'))

        today_date = date.today()
        now = datetime.now()

        employees = Employee.query.filter_by(is_active=True).all()
        for emp in employees:
            sched = get_schedule_for_day(emp.id, today_date)
            if not sched or sched.is_off:
                continue

            # Parse scheduled start time for today
            st_h, st_m = [int(x) for x in sched.start_time.split(':')]
            scheduled_start = datetime(today_date.year, today_date.month, today_date.day, st_h, st_m)
            notify_time = scheduled_start + timedelta(minutes=notify_min)

            # Only check if current time is past the notify threshold
            if now < notify_time:
                continue

            # Check if they've clocked in
            record = AttendanceRecord.query.filter_by(
                employee_id=emp.id, date=today_date
            ).first()

            if record and record.check_in:
                continue  # already checked in

            if record and record.late_notified:
                continue  # already notified

            # Send notification and mark
            send_late_email(emp.name, emp.employee_id, emp.department,
                           sched.start_time,
                           smtp_server, smtp_port, smtp_user, smtp_password,
                           admin_email, email_from)
            if not record:
                record = AttendanceRecord(employee_id=emp.id, date=today_date)
                db.session.add(record)
            record.late_notified = True
            db.session.commit()


def start_late_checker():
    """Start background thread for late check-in monitoring."""
    interval = app.config['LATE_CHECK_INTERVAL']
    
    def loop():
        while True:
            try:
                check_late_checkins()
            except Exception:
                logger.exception('迟到检查失败')
            time_module.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    logger.info('迟到检查已启动，间隔 %s 秒', interval)


def open_browser():
    """延迟打开浏览器。"""
    import threading
    def _open():
        import time
        time.sleep(1.5)
        import webbrowser
        webbrowser.open('http://127.0.0.1:5000')
    threading.Thread(target=_open, daemon=True).start()


if __name__ == '__main__':
    first_run_setup()
    # 非 PyInstaller 打包且是交互式终端时打开浏览器
    if not getattr(sys, 'frozen', False):
        open_browser()
    start_late_checker()
    url = f'http://0.0.0.0:5000'
    logger.info('考勤管理系统已启动')
    logger.info('本机访问: http://127.0.0.1:5000')
    logger.info('手机访问: http://<本机IP>:5000')
    logger.info('按 Ctrl+C 停止服务')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host='0.0.0.0', port=5000, debug=False)
