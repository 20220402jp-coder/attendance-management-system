# 考勤管理系统 — 项目进度 (2026-07-01)

## 今日改动总览

### 1. 项目清理
- 删除 PyInstaller 编译产物：`build/` (32MB), `dist/` (20MB), `考勤管理系统.spec`
- 删除 Docker 相关文件：`docker/` (26MB, 含 python-installer.exe)
- 删除部署脚本：`build.sh`, `deploy.sh`
- 删除 `=2.9`, `=3.1` 等垃圾文件
- 清理 `__pycache__/`
- **释放约 80MB 磁盘空间**

### 2. 打卡页面 (/) 界面调整
- 白色卡片拉长至页脚，flex 布局重写
- "考勤管理系统" → 移到页脚正中
- "中小企业打卡记录" → 从导航栏移除
- 语言选择器 → 从导航栏移入管理后台 → 邮件配置页面
- 导航栏剩余链接居中
- 模板添加 `TEMPLATES_AUTO_RELOAD = True` 避免修改后需重启

### 3. 二维码功能
- 卡片动态效果修复（SvgPathImage 替代 SvgImage）
- 弹窗新增 **「📥 下载 PDF」** 按钮（带脉冲光效动画）
- 删除"需在同一局域网"提示文本
- 新增 `/api/qrcode/print` 打印友好页面（自动弹出打印对话框）

### 4. 报班页面 (/schedule/) 优化
- 标题改为「📅 智能报班系统」
- 手机适配：日历单元格缩小（`min-height: 42px`）、间距压缩
- 保存按钮吸底（`position: sticky`），全宽显示

### 5. 统计页面 (/admin/stats) 大改
- **缺勤/请假支持**：统计现在遍历所有排班日，非休息日无记录则标记为「缺勤」
- **出勤天数修正**：缺勤/请假不计入出勤天数，独立统计
- **请假状态**：新增「请假」状态标签和图表颜色
- **CSV 导出**：同步包含所有排班日，缺勤/请假均有记录
- **默认日期范围**：改为上月1日至上月最后一日（如7月→6月1日~6月30日）
- **时区 Bug 修复**：`toISOString().split('T')[0]` 会转 UTC 导致日期偏移一天，改用本地时间拼接

### 6. 统计页面修复
- 修复 Chart.js 引用传参错误：`url_for('static', filename='chart.umd.min.js')`

### 7. 打卡记录修正功能（全新）
- **新增页面** `/admin/attendance` — 管理后台「📝 打卡修正」入口
- **API** `/api/attendance/records` — 查询指定员工+日期的记录
- **API** `/api/attendance/update` — 创建/更新记录，支持设置签到/签退时间
- **请假标记**：勾选「🛌 标记为请假」→ 清除签到签退时间，状态设为 `leave`
- **状态显示**：双时间为空时显示「— 未打卡」，请假显示「请假 🛌」
- **修复复选框双重切换 Bug**：点击复选框时原生勾选 + 事件冒泡二次勾选导致状态不动

### 8. 消息排队机制
- 新增 `queue.Queue` + 后台工作线程处理打卡请求
- 请求进队 → 工作线程逐一处理 → 返回结果
- 解决多人同时打卡时的并发写入冲突
- 监控接口：`GET /api/check/queue` 查看队列深度
- 前端打卡按钮文案改为「⏳ 排队中...」

### 9. 浏览器兼容性
- **移除 `backdrop-filter`**：从 `.clock-card`、`.stats-filters`、`.admin-form`、`.att-card` 等包含表单控件的元素移除，解决 Firefox 下日期选择器、输入框交互异常问题
- `.nav` 和 `.modal` 保留 `backdrop-filter`（不包含表单控件）

### 10. 其他修复
- 田中太郎验证码问题：清除 `pin_code='1234'`（代码 + 数据库双重清理）
- 打卡按钮文本居中（加上 `justify-content:center`）
- 排班选择器复选框点击事件处理优化
- 保存后自动刷新状态显示

---

## 当前项目结构

```
kaoqinguanli-new/attendance/
├── app.py                  # 主程序 (含排队机制、统计、打卡修正 API)
├── config.py               # 配置
├── models.py               # 数据模型
├── init_db.py              # 数据库初始化工具
├── input_prefs.py          # 测试数据填充工具
├── requirements.txt        # 依赖清单
├── start.sh                # 启动脚本
├── attendance.db           # SQLite 数据库
├── BUILD.md                # 构建文档
├── README.md               # 项目说明
├── venv/                   # Python 虚拟环境
├── static/
│   ├── style.css           # 全局样式
│   └── chart.umd.min.js    # Chart.js
├── templates/
│   ├── base.html           # 基础模板（导航栏 + 页脚）
│   ├── index.html          # 打卡页面
│   ├── schedule.html       # 报班页面
│   ├── admin.html          # 管理后台首页
│   ├── admin_employees.html # 员工管理
│   ├── admin_scheduling.html # 自动排班
│   ├── admin_stats.html    # 统计报表
│   ├── admin_attendance.html # 打卡记录修正
│   └── admin_settings.html # 邮件配置（含语言选择）
└── translations/
    ├── zh.json
    ├── en.json
    └── ja.json
```

## 已知待办

- 统计页面日期选择器使用原生 `<input type="date">`，Firefox 下交互体验有待优化
- 排班页面的 `toISOString()` 时区问题未修复
- 管理员没有登录认证（通过 URL 直接访问）
