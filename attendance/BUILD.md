# 📦 打包说明

> 开发完成后，将考勤管理系统打包成单文件可执行程序，用户双击即用。

---

## 原理

使用 **PyInstaller** 将 Python 解释器、项目代码、依赖库、模板文件全部打包进一个 ELF 可执行文件（Linux）或 .exe（Windows）。

用户电脑上**不需要装 Python、不需要装任何软件**。

---

## 环境要求（打包者用）

| 平台 | 要求 |
|---|---|
| Linux | Python 3.8+，已装 pip |
| Windows | Python 3.8+，已装 pip |

---

## Linux 打包

```bash
# 一键打包（自动创建 venv + 装 PyInstaller + 打包）
cd attendance/
bash build.sh

# 产物在 dist/考勤管理系统
```

或手动分步执行：

```bash
cd attendance/

# 1. 创建虚拟环境并装 PyInstaller
python3 -m venv venv
source venv/bin/activate
pip install pyinstaller

# 2. 打包
pyinstaller --onefile \
    --name "考勤管理系统" \
    --add-data "templates:templates" \
    --add-data "translations:translations" \
    --add-data "static:static" \
    --hidden-import flask_sqlalchemy \
    --hidden-import dateutil.parser \
    --hidden-import dateutil \
    --hidden-import email.mime.text \
    --hidden-import smtplib \
    --collect-all flask_sqlalchemy \
    app.py

# 产物在 dist/考勤管理系统
```

---

## Windows 打包

### 方案 A：在 Linux 上用 Docker 编译（推荐）

不需要 Windows 机器，也不需要装 Wine。

```bash
# 进入 docker/ 目录，执行打包脚本
cd attendance/docker/
bash build-windows.sh

# 产物在 dist/考勤管理系统.exe
```

第一次运行时会自动构建 Docker 镜像（内含 Wine + Windows Python + PyInstaller），后续打包秒出。

构建环境定义在 `docker/Dockerfile` 中，可自行修改 Python 版本等。

### 方案 B：在 Windows 上直接打包

```powershell
# 在 Windows 上打开 PowerShell 或 CMD，进入 attendance 目录

# 1. 装 PyInstaller
pip install pyinstaller

# 2. 打包
pyinstaller --onefile --name "考勤管理系统" ^
    --add-data "templates;templates" ^
    --add-data "translations;translations" ^
    --add-data "static;static" ^
    --hidden-import flask_sqlalchemy ^
    --hidden-import dateutil.parser ^
    --hidden-import dateutil ^
    --hidden-import email.mime.text ^
    --hidden-import smtplib ^
    --collect-all flask_sqlalchemy ^
    app.py

# 产物在 dist\考勤管理系统.exe
```

> **注意**：Windows 上 `--add-data` 用 `;` 分隔路径，Linux 用 `:`。

> **注意**：Windows 上 `--add-data` 用 `;` 分隔路径，Linux 用 `:`。

---

## 打包产物

| 平台 | 文件 | 大小 |
|---|---|---|
| Linux | `dist/考勤管理系统` | ~20MB |
| Windows | `dist\考勤管理系统.exe` | ~35MB |

---

## 分发说明

把 `dist/考勤管理系统`（或 `.exe`）发给用户即可。

### 用户首次使用流程

```
双击运行
  ↓
浏览器自动弹出打卡页面（http://127.0.0.1:5000）
  ↓
可直接用示例员工（张三 / 田中太郎 / John Smith）体验
  ↓
管理员进入 http://127.0.0.1:5000/admin/ 管理
```

### 运行机制

- 数据库 `attendance.db` 自动生成在可执行文件**旁边**
- 所有打卡记录、员工数据都存在这个文件里
- 备份只备份这个 `.db` 文件即可
- 关闭终端或按 `Ctrl+C` 停止服务

---

## 开发期间运行（不打包）

```bash
cd attendance/
source venv/bin/activate     # Windows: venv\Scripts\activate
python app.py
```

浏览器打开 `http://127.0.0.1:5000`

---

## 常见问题

**Q: 打包出的文件太大？**
A: ~20MB 正常，因为包含了 Python 解释器和所有依赖库。

**Q: 能在 32 位系统上跑吗？**
A: 在 32 位机器上打包就能跑 32 位版本。

**Q: 更新代码后需要重新打包吗？**
A: 是的，每次修改代码后重新跑 `build.sh` 即可。

**Q: 数据库文件在哪？**
A: 在可执行文件所在的目录下，文件名 `attendance.db`。
