# 📋 考勤打卡系统 (Attendance System)

小企业专用的签到打卡 + 智能排班系统。支持多语言（中文/English/日本語），
每个人独立上下班时间，智能排班，统计报表，打卡记录修正，请假管理。

---

## 目录

- [技术栈](#技术栈)
- [快速启动](#快速启动)
- [项目结构](#项目结构)
- [页面说明](#页面说明)
- [功能详解](#功能详解)
- [数据模型](#数据模型)
- [排班算法说明](#排班算法说明)
- [通知系统](#通知系统)
- [API 参考](#api-参考)
- [开发踩坑记录](#开发踩坑记录)
- [FAQ](#faq)

---

## 技术栈

| 层 | 技术 | 选型理由 |
|---|---|---|
| 后端 | Python Flask | 轻量、零配置、适合本地部署 |
| 数据库 | SQLite + SQLAlchemy ORM | 单文件数据库，小规模团队完全够用 |
| 前端 | 原生 HTML + CSS + JavaScript | 不引入框架，减少依赖 |
| 图表 | Chart.js (本地) | 统计面板 |
| 多语言 | 自定义 JSON 文件 + Flask context processor | 比 Flask-Babel 更轻量 |
| 排队 | Python queue.Queue + 后台线程 | 处理多人同时打卡并发 |

## 快速启动

```bash
# macOS / Linux
cd attendance
bash start.sh

# 打开浏览器
# http://localhost:5000
```

`start.sh` 会把虚拟环境创建在项目目录外，并在首次运行时自动安装依赖。
首次启动会自动创建空数据库和所有数据表，不会加入示例员工。请进入「管理 → 员工管理」添加第一位员工。

如需指定外部虚拟环境位置：

```bash
ATTENDANCE_VENV_DIR=/path/to/venv bash start.sh
```

## 项目结构

```
attendance/
├── app.py                 # Flask 主程序
├── config.py              # 配置
├── models.py              # 数据库模型
├── init_db.py             # 数据库初始化工具
├── input_prefs.py         # 模拟员工偏好数据（测试用）
├── requirements.txt       # 依赖清单
├── start.sh               # 启动脚本
├── PROGRESS.md            # 项目进度说明
├── README.md              # 本文件
├── attendance.db          # 运行时自动生成，不上传 GitHub
├── static/
│   ├── style.css          # 全局样式
│   └── chart.umd.min.js   # Chart.js
├── templates/
│   ├── base.html          # 基础模板
│   ├── index.html         # 打卡页（签到/签退）
│   ├── schedule.html      # 报班页（员工提交偏好）
│   ├── admin.html         # 管理后台首页
│   ├── admin_employees.html # 员工管理 + 个人排班表
│   ├── admin_scheduling.html # 自动排班 + 拖拽调整
│   ├── admin_stats.html   # 统计报表
│   ├── admin_attendance.html # 打卡记录修正
│   └── admin_settings.html # 邮件配置 + 语言选择
└── translations/
    ├── zh.json            # 中文
    ├── en.json            # 英文
    └── ja.json            # 日文
```

---

## 页面说明

### 打卡页 `/`（员工用）

选择姓名 → 验证码（如设置）→ 点击「签到上班」或「签退下班」。

- 签退时会检查当前时间是否在排班时间内
- 签退后自动计算当日工时（扣除午休）
- 状态自动判断：正常 / 迟到 / 早退 / 迟到+早退
- 多人同时打卡时自动排队，按顺序处理

### 报班页 `/schedule/`（员工用）

标题：**智能报班系统**

选择姓名 → 在日历上点击每天 → 切换「上班 / 休息 / 都可以」→ 保存。

手机友好：日历格子自适应，保存按钮吸底。

### 管理后台 `/admin/`

导航栏在 `/admin/` 路径下自动切换为管理员链接。

#### 员工管理 `/admin/employees`

- 添加/编辑/删除员工
- 每个员工有工号、姓名、部门、语言偏好、验证码（可选）
- 点击「📅 排班表」设置个人上下班时间

#### 自动排班 `/admin/schedule`

核心功能，分三步：

1. **设定每日人数要求**
2. **员工偏好** — 从 `/schedule/` 读取
3. **自动排班** → 算法生成排班表

支持拖拽调整：同一列异状态互换。

#### 统计报表 `/admin/stats`

- 选择员工 + 日期范围（默认上月整月）
- 按排班表列出所有排班日，无打卡记录的工作日显示为「缺勤」
- 管理员可标记「请假」— 状态显示为「请假」，不计入缺勤
- 汇总卡片：出勤/排班天数、总工时、平均工时、迟到/早退/缺勤/请假次数
- **CSV 导出** — 包含所有排班日，缺勤/请假均有记录

#### 打卡记录修正 `/admin/attendance`

管理员补签/修改员工打卡记录：

- 选择员工 → 选择日期 → 点「🔍 查询」
- 修改签到/签退时间 → 点「💾 保存」
- **🛌 标记为请假** — 勾选后清除签到时间，状态设为「请假」
- 无记录时填入时间保存即可创建新记录

#### 邮件配置 `/admin/settings`

配置迟到通知邮件，底部有语言选择器。

---

## 功能详解

### 打卡排队机制

多人同时打卡时，请求进入线程安全队列，后台工作线程逐一处理，避免数据库写冲突。

- 监控：`GET /api/check/queue` 查看队列深度
- 前端按钮显示「⏳ 排队中...」

### 请假管理

考勤统计按排班表计算，缺勤日自动标记。管理员在打卡修正页面勾选「标记为请假」：

- 清除签到/签退时间
- 状态设为 `leave`
- 统计时计入「请假」而不计入「缺勤」
- CSV 导出同步区分

### 工时计算

```
实际工时 = (签退时间 - 签到时间) - 午休重合部分

午休：12:00 - 13:00（可配置）
仅当工作时间段与午休有重叠时扣除

全职员工：统计出勤天数
兼职员工：统计整点工时（不满 1 小时不计）
```

### 迟到 / 早退判断

```
迟到：签到时间 > 排班上班时间 + 宽限期（默认30分钟）
早退：签退时间 < 排班下班时间
状态：正常 / 迟到 / 早退 / 迟到+早退 / 缺勤 / 未签退 / 请假
```

### 二维码打卡

管理后台首页点击「📱 打卡二维码」→ 生成当前局域网地址的二维码。
手机扫码直达打卡页面。
支持 **下载 PDF**（打印对话框 → 另存为 PDF）。

### 多语言切换

语言选择器在管理后台 → 邮件配置页面底部。
支持 中文 / English / 日本語。翻译文件在 `translations/`。

### 通知系统

后台线程每 60 秒检查一次，谁到了上班时间 + 阈值分钟还没签到，发邮件通知管理员。

---

## 数据模型

```
employees               # 员工表
├── employee_id         # 工号（唯一）
├── name                # 姓名
├── department          # 部门
├── lang                # 语言偏好
├── pin_code            # 验证码（可选）
└── is_active           # 是否启用

schedules               # 个人班次表
├── employee_id
├── day_of_week         # 0=周一 ... 6=周日
├── start_time
├── end_time
└── is_off

attendance_records      # 打卡记录表
├── employee_id
├── date
├── check_in / check_out
├── status              # normal/late/early_leave/both/absent/partial/leave
├── working_hours
├── late_notified
└── note

schedule_preferences    # 员工排班偏好
├── employee_id
├── date
└── preference          # want_work / want_off / flexible

schedule_assignments    # 排班结果
├── employee_id
├── date
├── is_working
└── source

settings                # 配置表（键值对）
├── key
└── value
```

---

## 排班算法说明

见下方[排班算法说明](#排班算法说明)。

---

## API 参考

### 打卡

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 打卡页面 |
| GET | `/api/today/<employee_id>` | 获取员工今日状态 |
| POST | `/api/check` | 签到/签退（排队处理） |
| GET | `/api/check/queue` | 查看排队深度 |
| GET | `/api/qrcode?url=` | 生成二维码 SVG |
| GET | `/api/qrcode/print` | 二维码打印/PDF 页面 |
| GET | `/api/server-info` | 获取服务器局域网地址 |

### 员工管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/employees` | 员工管理页面 |
| POST | `/api/employee` | 添加员工 |
| PUT | `/api/employee/<id>` | 编辑员工 |
| DELETE | `/api/employee/<id>` | 删除员工 |
| GET/POST | `/api/employee/<id>/schedules` | 获取/保存排班时间 |

### 排班

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/schedule/` | 偏好提交页面 |
| GET | `/api/schedule/preferences/<eid>` | 获取员工偏好 |
| POST | `/api/schedule/preferences` | 保存员工偏好 |
| GET | `/admin/schedule` | 自动排班页面 |
| POST | `/api/schedule/auto` | 执行自动排班 |
| GET | `/api/schedule/result` | 获取排班结果 |
| POST | `/api/schedule/update` | 手动修改排班 |
| POST | `/api/schedule/simulate` | 模拟员工偏好（测试用） |

### 统计/打卡修正

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/stats` | 统计页面 |
| POST | `/api/stats` | 查询考勤数据 |
| POST | `/api/stats/summary` | 获取统计摘要 |
| POST | `/api/stats/export` | 导出 CSV |
| GET | `/admin/attendance` | 打卡修正页面 |
| POST | `/api/attendance/records` | 查询某日记录 |
| POST | `/api/attendance/update` | 创建/更新记录（支持请假） |

### 设置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/settings` | 邮件配置页面 |
| GET/POST | `/api/settings` | 读取/保存配置 |
| POST | `/api/settings/test-email` | 测试邮件发送 |

---

## 开发踩坑记录

### 1. `toISOString()` 时区偏移

**问题**：`new Date().toISOString().split('T')[0]` 得到的日期比本地日期少一天。

**原因**：`toISOString()` 转成 UTC（+0），中国 UTC+8 的凌晨会被推到前一天的 UTC 时间。

**解决**：用本地年/月/日拼接：

```javascript
function localDate(d) {
    return d.getFullYear() + '-' +
           String(d.getMonth()+1).padStart(2,'0') + '-' +
           String(d.getDate()).padStart(2,'0');
}
```

### 2. `backdrop-filter` 与原生表单控件冲突

**问题**：`backdrop-filter` 在 Firefox 下导致 `<input type="date">` 的日期选择弹窗无法点击。

**解决**：包含表单控件的元素移除 `backdrop-filter`（`.clock-card`、`.stats-filters`、`.admin-form`、`.att-card` 等）。

### 3. Flask 模板缓存

**问题**：生产模式（debug=False）下 Jinja2 缓存模板，编辑后不生效。

**解决**：添加 `app.config['TEMPLATES_AUTO_RELOAD'] = True`。

### 4. 复选框双重切换

**问题**：点击复选框 → 浏览器原生勾选 → 事件冒泡到父容器 → JavaScript 再次切换 → 状态回退。

**解决**：事件处理函数判断目标元素，复选框本身触发时不重复切换。

### 5. url_for 传参错误

**问题**：`url_for('static', 'file.js')` 在 Flask 3.x 需要 `filename=` 关键字参数。

**正确写法**：`url_for('static', filename='file.js')`。

---

## FAQ

**Q: 员工忘了打卡怎么办？**
A: 管理员在「打卡修正」页面填入时间和日期保存即可补签。

**Q: 员工请假怎么办？**
A: 管理员在「打卡修正」页面勾选「🛌 标记为请假」后保存，统计时显示为请假。

**Q: 数据库文件在哪？**
A: `attendance/attendance.db`。该文件由程序自动创建，Git 会忽略它。

**Q: 如何备份？**
```bash
cp ~/attendance/attendance.db ~/backup_$(date +%Y%m%d).db
```

**Q: 如何重置所有打卡记录但保留员工？**
```bash
cd ~/attendance && source venv/bin/activate
python -c "
from models import db, AttendanceRecord, SchedulePreference, ScheduleAssignment
from app import app
with app.app_context():
    AttendanceRecord.query.delete()
    SchedulePreference.query.delete()
    ScheduleAssignment.query.delete()
    db.session.commit()
    print('Cleared')
"
```
