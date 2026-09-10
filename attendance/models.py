import calendar
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, time, timedelta
from dateutil import parser as dtparser

db = SQLAlchemy()


class Employee(db.Model):
    __tablename__ = 'employees'

    id           = db.Column(db.Integer, primary_key=True)
    employee_id  = db.Column(db.String(20), unique=True, nullable=False)
    name         = db.Column(db.String(100), nullable=False)
    department   = db.Column(db.String(100), default='')
    lang         = db.Column(db.String(5), default='zh')
    is_active    = db.Column(db.Boolean, default=True)
    rest_days    = db.Column(db.String(20), default='')  # 固定休息日，如 "5,6" 表示周六日
    min_rest_per_week = db.Column(db.Integer, default=2)  # 每周最少休息天数
    created_at   = db.Column(db.DateTime, default=datetime.now)

    schedules    = db.relationship('Schedule', backref='employee', lazy='dynamic',
                                   cascade='all, delete-orphan')
    records      = db.relationship('AttendanceRecord', backref='employee', lazy='dynamic',
                                   cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Employee {self.employee_id} {self.name}>'


class Schedule(db.Model):
    __tablename__ = 'schedules'

    id           = db.Column(db.Integer, primary_key=True)
    employee_id  = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    day_of_week  = db.Column(db.Integer, nullable=False)
    start_time   = db.Column(db.String(5), nullable=False)
    end_time     = db.Column(db.String(5), nullable=False)
    is_off       = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Schedule {self.employee_id} dow={self.day_of_week} {self.start_time}-{self.end_time}>'


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id            = db.Column(db.Integer, primary_key=True)
    employee_id   = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date          = db.Column(db.Date, nullable=False)
    check_in      = db.Column(db.DateTime, nullable=True)
    check_out     = db.Column(db.DateTime, nullable=True)
    status        = db.Column(db.String(20), default='normal')
    working_hours = db.Column(db.Float, nullable=True)
    note          = db.Column(db.Text, default='')
    late_notified = db.Column(db.Boolean, default=False)  # late email sent?
    created_at    = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'date', name='uix_employee_date'),
    )

    def __repr__(self):
        return f'<Attendance {self.employee_id} {self.date}>'


# ── Helper functions ──────────────────────────────────────────────

def get_schedule_for_day(employee_id, dt_date: date):
    """Return the Schedule for a given employee on this weekday, or None."""
    dow = dt_date.weekday()
    return Schedule.query.filter_by(
        employee_id=employee_id,
        day_of_week=dow
    ).first()


def compute_working_hours(check_in: datetime, check_out: datetime,
                          lunch_start='12:00', lunch_end='13:00'):
    """Compute hours worked, subtracting lunch overlap."""
    if not check_in or not check_out:
        return None
    total = (check_out - check_in).total_seconds() / 3600.0

    ls = time(*[int(x) for x in lunch_start.split(':')])
    le = time(*[int(x) for x in lunch_end.split(':')])
    ci_time = check_in.time()
    co_time = check_out.time()

    if ci_time < le and co_time > ls:
        lunch_start_dt = datetime.combine(check_in.date(), ls)
        lunch_end_dt   = datetime.combine(check_out.date(), le)
        overlap_start  = max(check_in, lunch_start_dt)
        overlap_end    = min(check_out, lunch_end_dt)
        if overlap_end > overlap_start:
            lunch_hours = (overlap_end - overlap_start).total_seconds() / 3600.0
            total -= lunch_hours
    return round(total, 2)


def compute_status(check_in, check_out, schedule, grace_minutes=30):
    """Determine attendance status."""
    if not schedule or schedule.is_off:
        return 'absent', 0.0

    st = dtparser.parse(schedule.start_time).time()
    et = dtparser.parse(schedule.end_time).time()

    late = False
    early = False

    if check_in:
        grace_delta = timedelta(minutes=grace_minutes)
        grace_limit = datetime.combine(check_in.date(), st) + grace_delta
        if check_in > grace_limit:
            late = True

    if check_out:
        co = check_out.time()
        if co < et:
            early = True

    if late and early:
        return 'both', None
    if late:
        return 'late', None
    if early:
        return 'early_leave', None
    return 'normal', None


# ── Scheduling models ────────────────────────────────────────────

class SchedulePreference(db.Model):
    """Employee's work preference for a specific date."""
    __tablename__ = 'schedule_preferences'

    id          = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    preference  = db.Column(db.String(10), nullable=False)  # want_work / want_off / flexible
    created_at  = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'date', name='uix_pref_employee_date'),
    )


class Setting(db.Model):
    """Key-value settings (email config, etc)."""
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, default='')

    @classmethod
    def get(cls, key, default=''):
        s = cls.query.filter_by(key=key).first()
        return s.value if s else default

    @classmethod
    def set(cls, key, value):
        s = cls.query.filter_by(key=key).first()
        if s:
            s.value = value
        else:
            db.session.add(cls(key=key, value=value))
        db.session.commit()


class ScheduleAssignment(db.Model):
    """Final schedule assignment for a date."""
    __tablename__ = 'schedule_assignments'

    id          = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    is_working  = db.Column(db.Boolean, default=True)
    source      = db.Column(db.String(20), default='auto')  # auto / manual / swap
    note        = db.Column(db.Text, default='')
    created_at  = db.Column(db.DateTime, default=datetime.now)

    employee    = db.relationship('Employee', backref='sched_assignments')

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'date', name='uix_assign_employee_date'),
    )


class ClockTicket(db.Model):
    """Persistent idempotency key and result for the shared clock client."""
    __tablename__ = 'clock_tickets'
    id = db.Column(db.String(36), primary_key=True)
    employee_id = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    day = db.Column(db.String(10), nullable=False)
    process_id = db.Column(db.String(32), nullable=False, default=lambda: __import__('os').environ.get('ATTENDANCE_PROCESS_ID', ''))
    result = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
