"""考勤规则：应出勤判定、状态与工时计算。

这里不依赖浏览器请求，方便单独测试。所有页面（打卡、统计、今日一览、
导出、迟到提醒）都通过本模块得到同一个结论，避免各算各的。
"""

from datetime import datetime, time, timedelta

from models import Schedule, ScheduleAssignment, Setting

# 设置表里的键 -> 默认值。空值一律回落到默认值。
RULE_DEFAULTS = {
    'work_start': '09:00',
    'work_end': '18:00',
    'lunch_enabled': '1',
    'lunch_start': '12:00',
    'lunch_end': '13:00',
    'grace_minutes': '30',
}
RULE_KEYS = tuple(RULE_DEFAULTS)

# 没有设置跨夜班次时，凌晨这个时间之前仍可为前一天签退（例如餐饮店打烊）。
DAY_CUTOFF = time(5, 0)
# 跨夜班次结束后，仍允许签退的宽限时间。
OVERNIGHT_SLACK = timedelta(hours=6)


def parse_hm(value):
    """把 'HH:MM' 解析为 time；格式不对时抛出 ValueError。"""
    hour, minute = str(value).strip().split(':')[:2]
    return time(int(hour), int(minute))


def clean_rules(data):
    """校验后台提交的规则，返回可直接保存的 {键: 字符串}。"""
    cleaned = {}
    for key in ('work_start', 'work_end', 'lunch_start', 'lunch_end'):
        if key in data:
            cleaned[key] = parse_hm(data[key]).strftime('%H:%M')
    if 'lunch_enabled' in data:
        cleaned['lunch_enabled'] = '1' if str(data['lunch_enabled']).lower() in ('1', 'true', 'on', 'yes') else '0'
    if 'grace_minutes' in data:
        minutes = int(data['grace_minutes'])
        if not 0 <= minutes <= 240:
            raise ValueError('grace_minutes')
        cleaned['grace_minutes'] = str(minutes)
    return cleaned


def get_rules():
    """读取当前规则；任何一项缺失或损坏都使用默认值。"""
    stored = {row.key: row.value for row in Setting.query.filter(Setting.key.in_(RULE_KEYS)).all()}
    rules = {}
    for key, default in RULE_DEFAULTS.items():
        value = stored.get(key) or default
        try:
            if key == 'grace_minutes':
                rules[key] = int(value)
            elif key == 'lunch_enabled':
                rules[key] = value == '1'
            else:
                rules[key] = parse_hm(value).strftime('%H:%M')
        except (TypeError, ValueError):
            rules[key] = clean_default(key)
    return rules


def clean_default(key):
    default = RULE_DEFAULTS[key]
    if key == 'grace_minutes':
        return int(default)
    if key == 'lunch_enabled':
        return default == '1'
    return default


class ShiftBook:
    """一次性读入若干员工在一段日期内的班次依据。

    判定顺序：
    1. 入职（建档）之前不算应出勤；
    2. 当天有排班结果时，以排班结果为准（上班 / 休息）；
    3. 否则按每周固定班次；
    4. 都没有则视为休息。休息日仍然可以打卡，只是不会记缺勤或迟到。
    """

    def __init__(self, employee_ids, start, end, rules=None):
        self.rules = rules or get_rules()
        employee_ids = list(employee_ids)
        self.weekly = {}
        self.assigned = {}
        if not employee_ids:
            return
        for row in Schedule.query.filter(Schedule.employee_id.in_(employee_ids)).all():
            self.weekly[(row.employee_id, row.day_of_week)] = row
        for row in ScheduleAssignment.query.filter(
            ScheduleAssignment.employee_id.in_(employee_ids),
            ScheduleAssignment.date >= start,
            ScheduleAssignment.date <= end,
        ).all():
            self.assigned[(row.employee_id, row.date)] = row

    def shift(self, employee, day):
        """返回当天班次 {'start','end','start_dt','end_dt'}；休息返回 None。"""
        if employee.created_at and day < employee.created_at.date():
            return None
        weekly = self.weekly.get((employee.id, day.weekday()))
        weekly_times = None
        if weekly is not None and not weekly.is_off:
            weekly_times = (weekly.start_time, weekly.end_time)
        assigned = self.assigned.get((employee.id, day))
        if assigned is not None:
            if not assigned.is_working:
                return None
            times = weekly_times or (self.rules['work_start'], self.rules['work_end'])
        elif weekly_times:
            times = weekly_times
        else:
            return None
        try:
            start_t, end_t = parse_hm(times[0]), parse_hm(times[1])
        except (TypeError, ValueError):
            start_t, end_t = parse_hm(self.rules['work_start']), parse_hm(self.rules['work_end'])
        start_dt = datetime.combine(day, start_t)
        end_dt = datetime.combine(day, end_t)
        if end_dt <= start_dt:  # 跨夜班次，例如 22:00 – 06:00
            end_dt += timedelta(days=1)
        return {
            'start': start_t.strftime('%H:%M'),
            'end': end_t.strftime('%H:%M'),
            'start_dt': start_dt,
            'end_dt': end_dt,
        }


def working_hours(check_in, check_out, rules):
    """实际工时（小时，保留两位），按规则扣除与午休重叠的时间。"""
    if not check_in or not check_out or check_out <= check_in:
        return None if not check_in or not check_out else 0.0
    seconds = (check_out - check_in).total_seconds()
    if rules['lunch_enabled']:
        lunch_start, lunch_end = parse_hm(rules['lunch_start']), parse_hm(rules['lunch_end'])
        day = check_in.date()
        while day <= check_out.date():
            begin = max(check_in, datetime.combine(day, lunch_start))
            finish = min(check_out, datetime.combine(day, lunch_end))
            if finish > begin:
                seconds -= (finish - begin).total_seconds()
            day += timedelta(days=1)
    return round(max(seconds, 0) / 3600.0, 2)


def overnight_open(day, shift, now):
    """前一天签到但未签退的记录，现在是否仍应视为「还在上班」。"""
    if shift and shift['end_dt'].date() > day:
        return now <= shift['end_dt'] + OVERNIGHT_SLACK
    return now.date() == day + timedelta(days=1) and now.time() < DAY_CUTOFF


def evaluate(record, shift, rules, now, day):
    """综合记录与班次给出结论。

    返回 {'status', 'hours', 'late', 'early'}。status 为 None 表示这天无需显示
    （休息且没有打卡，或还没到的日子）。
    """
    result = {'status': None, 'hours': None, 'late': False, 'early': False}
    if record is not None and record.status == 'leave':
        result['status'] = 'leave'
        return result
    check_in = record.check_in if record is not None else None
    check_out = record.check_out if record is not None else None
    grace = timedelta(minutes=rules['grace_minutes'])

    if not check_in:
        if not shift or day > now.date():
            return result
        if day == now.date() and now <= shift['start_dt'] + grace:
            result['status'] = 'pending'
        else:
            result['status'] = 'absent'
        return result

    if shift and check_in > shift['start_dt'] + grace:
        result['late'] = True
    if not check_out:
        still_working = day == now.date() or overnight_open(day, shift, now)
        result['status'] = 'working' if still_working else 'partial'
        return result

    result['hours'] = working_hours(check_in, check_out, rules)
    if shift and check_out < shift['end_dt']:
        result['early'] = True
    if result['late'] and result['early']:
        result['status'] = 'both'
    elif result['late']:
        result['status'] = 'late'
    elif result['early']:
        result['status'] = 'early_leave'
    else:
        result['status'] = 'normal'
    return result
