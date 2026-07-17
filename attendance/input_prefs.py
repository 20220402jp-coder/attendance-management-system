"""Fill simulated preferences into the system for testing."""
import sys
sys.path.insert(0, '/home/xu/attendance')
from app import app
from models import db, Employee, SchedulePreference, ScheduleAssignment
from datetime import date, timedelta

# Employee IDs
emps = {
    'R001': '张三',  # 长勤
    'R002': '李四',  # 长勤
    'T001': '王五',  # 临时
    'T002': '赵六',  # 临时
    'T003': '孙七',  # 临时
    'T004': '周八',  # 临时
    'T005': '吴九',  # 临时
}

# Next month: July 2026
Y, M = 2026, 7

def d(day):
    return date(Y, M, day)

with app.app_context():
    # Clear old preferences & assignments for July
    start = d(1)
    end = d(31)
    SchedulePreference.query.filter(
        SchedulePreference.date >= start,
        SchedulePreference.date <= end,
    ).delete()
    ScheduleAssignment.query.filter(
        ScheduleAssignment.date >= start,
        ScheduleAssignment.date <= end,
    ).delete()
    db.session.commit()

    def add_pref(eid, day, pref):
        emp = Employee.query.filter_by(employee_id=eid).first()
        if emp:
            existing = SchedulePreference.query.filter_by(
                employee_id=emp.id, date=d(day)
            ).first()
            if existing:
                existing.preference = pref
            else:
                db.session.add(SchedulePreference(
                    employee_id=emp.id, date=d(day), preference=pref
                ))

    def add_range(eid, days, pref):
        for day in days:
            add_pref(eid, day, pref)

    # ── 张三 (长勤) ──
    # 周休2天, 自选的休息日
    zhang_off = [2,3, 8,9, 14,17, 22,24, 27,30]
    add_range('R001', range(1, 32), 'flexible')
    add_range('R001', zhang_off, 'want_off')
    # 其余默认上班 - only mark some as want_work to be clear
    for day in range(1, 32):
        if day not in zhang_off:
            add_pref('R001', day, 'want_work')

    # ── 李四 (长勤) ──
    li_off = [1,3, 7,10, 14,16, 21,23, 28,31]
    add_range('R002', range(1, 32), 'flexible')
    add_range('R002', li_off, 'want_off')
    for day in range(1, 32):
        if day not in li_off:
            add_pref('R002', day, 'want_work')

    # ── 王五 (临时) ──
    wang_work = [1,3,6,10,13,15,17,20,24,27,29,31]
    wang_off = [8,22]
    add_range('T001', range(1, 32), 'flexible')
    add_range('T001', wang_work, 'want_work')
    add_range('T001', wang_off, 'want_off')

    # ── 赵六 (临时) ──
    zhao_work = [2,6,14,15,16]
    zhao_off = [4,5,18,19,25,26]
    add_range('T002', range(1, 32), 'flexible')
    add_range('T002', zhao_work, 'want_work')
    add_range('T002', zhao_off, 'want_off')

    # ── 孙七 (临时) ──
    sun_work = [1,2,3,13,14,15,16,17]
    sun_off = [20,21,22,23,24,25,26]
    add_range('T003', range(1, 32), 'flexible')
    add_range('T003', sun_work, 'want_work')
    add_range('T003', sun_off, 'want_off')

    # ── 周八 (临时) ──
    zhou_off = [1,15,30]
    add_range('T004', range(1, 32), 'flexible')
    add_range('T004', zhou_off, 'want_off')

    # ── 吴九 (临时) ──
    wu_work = [6,7,8,9,10,20,21,22,23,24]
    wu_off = [13,14,15,16,17,27,28,29,30,31]
    add_range('T005', range(1, 32), 'flexible')
    add_range('T005', wu_work, 'want_work')
    add_range('T005', wu_off, 'want_off')

    db.session.commit()

    # Print summary
    print("=== 偏好已录入 ===\n")
    for eid, ename in emps.items():
        emp = Employee.query.filter_by(employee_id=eid).first()
        prefs = SchedulePreference.query.filter(
            SchedulePreference.employee_id == emp.id,
            SchedulePreference.date >= start,
            SchedulePreference.date <= end,
        ).order_by(SchedulePreference.date).all()

        counts = {'want_work': 0, 'want_off': 0, 'flexible': 0}
        for p in prefs:
            counts[p.preference] = counts.get(p.preference, 0) + 1
        print(f"{ename} ({eid}): 上班{counts['want_work']}天, 休息{counts['want_off']}天, 灵活{counts['flexible']}天")

    print("\n总计:", SchedulePreference.query.filter(
        SchedulePreference.date >= start,
        SchedulePreference.date <= end,
    ).count(), "条记录")
