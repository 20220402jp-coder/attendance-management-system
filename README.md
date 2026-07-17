<h1 align="center">📋 考勤打卡系统</h1>

<h2 align="center">中文 ｜ <a href="README.ja.md">日本語</a> ｜ <a href="README.en.md">English</a></h2>

<h1>下载程序</h1>

<h2>🪟 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.0/AttendanceSystem-1.0.0-Windows-x64.exe.zip">Windows 电脑点这里下载</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.0/AttendanceSystem-1.0.0-macOS-arm64.zip">Mac 电脑点这里下载（M1、M2、M3、M4 芯片）</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.0/AttendanceSystem-1.0.0-macOS-x64.zip">Intel 芯片的 Mac 点这里下载</a></h2>

<h2>🐧 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.0/AttendanceSystem-1.0.0-Linux-x64.zip">Linux 电脑点这里下载</a></h2>

这是为需要简单考勤和排班工具的小企业制作的系统，支持中文、英文和日文。

<h1>怎么使用</h1>

<h2>1. 下载对应的文件</h2>

<h2>2. 把下载的压缩包解压</h2>

<h2>3. 双击里面的程序</h2>

程序启动后会自动打开网页。第一次使用时，请打开「管理 → 员工管理」添加员工。关闭程序窗口即可停止系统。

### Windows 如果出现安全提醒

点击「更多信息」，再点击「仍要运行」。

### Mac 如果无法打开

右键点击程序，选择「打开」。如果仍然被拦截，请到「系统设置 → 隐私与安全性」点击「仍要打开」。

### Linux 如果无法双击运行

```bash
chmod +x AttendanceSystem-*-Linux-*
```

本程序不需要安装 Python 或其他软件。

<h2>📖 <a href="USER_GUIDE.md">点这里打开完整使用说明</a></h2>

---

<details>
<summary><strong>开发和技术说明（使用程序时不需要看）</strong></summary>

## 目录

- [技术栈](#技术栈)
- [快速启动](#快速启动)
- [项目结构](#项目结构)
- [数据模型](#数据模型)
- [排班算法说明](#排班算法说明)
- [通知系统](#通知系统)
- [API 参考](#api-参考)
- [开发踩坑记录](#开发踩坑记录)
- [数据维护](#数据维护)

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

## 开发者：从源码启动

```bash
# macOS / Linux
cd attendance
bash start.sh

# Windows
cd attendance
start.bat

# 打开浏览器
# http://localhost:5000
```

`start.sh` 会把虚拟环境创建在项目目录外，并在首次运行时自动安装依赖。
首次启动会自动创建空数据库和所有数据表，不会加入示例员工。请进入「管理 → 员工管理」添加第一位员工。

如需指定外部虚拟环境位置：

```bash
ATTENDANCE_VENV_DIR=/path/to/venv bash start.sh
```

### 运行日志

默认日志位于当前用户的正式数据目录中：

```text
Windows: %LOCALAPPDATA%\AttendanceSystem\logs\attendance.log
macOS:   ~/Library/Application Support/AttendanceSystem/logs/attendance.log
Linux:   ~/.local/share/attendance-system/logs/attendance.log
```

日志同时显示在终端，单个文件最大 2MB，最多保留 5 份旧日志。如需指定位置：

```bash
ATTENDANCE_LOG_DIR=/path/to/logs bash start.sh
```

## 项目结构

```
attendance/
├── app.py                 # Flask 主程序
├── database.py            # 数据库升级
├── config.py              # 配置
├── models.py              # 数据库模型
├── init_db.py             # 数据库初始化工具
├── requirements.txt       # 依赖清单
├── start.sh               # macOS/Linux 源码启动
├── start.bat              # Windows 源码启动
├── build.py               # 跨平台打包入口
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

## 数据模型

```
employees               # 员工表
├── employee_id         # 工号（唯一）
├── name                # 姓名
├── department          # 部门
├── lang                # 语言偏好
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

## 数据维护

**Q: 数据库文件在哪？**
A: 程序会按操作系统自动保存到当前用户的数据目录：

```text
Windows: %LOCALAPPDATA%\AttendanceSystem\attendance.db
macOS:   ~/Library/Application Support/AttendanceSystem/attendance.db
Linux:   ~/.local/share/attendance-system/attendance.db
```

数据库不在源码目录内，不会上传 GitHub，更新或替换程序也不会覆盖数据。

**Q: 如何备份？**
```bash
cp "$HOME/Library/Application Support/AttendanceSystem/attendance.db" "$HOME/backup_$(date +%Y%m%d).db"
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

</details>
