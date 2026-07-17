# 开发说明

本文档供继续维护本项目的开发人员使用，普通使用者不需要阅读。

## 本地启动

```bash
# macOS / Linux
cd attendance
bash start.sh

# Windows
cd attendance
start.bat
```

首次启动会在项目目录外创建虚拟环境，并在当前用户的数据目录创建空数据库。

## 数据和日志位置

```text
Windows: %LOCALAPPDATA%\AttendanceSystem
macOS:   ~/Library/Application Support/AttendanceSystem
Linux:   ~/.local/share/attendance-system
```

这里保存数据库、程序密钥和日志，不会随源代码上传或打进安装包。

## 测试

```bash
cd attendance
python -m pytest -q ../tests
```

每次修改后都应运行测试并实际启动程序，确认首页和管理页面可以打开。

## 打包

推送普通代码不会自动打包。创建版本标签后，GitHub 会分别生成 Windows、macOS 和 Linux 程序。

本地打包命令：

```bash
cd attendance
python build.py
```

## 主要文件

- `attendance/app.py`：页面和主要功能
- `attendance/models.py`：数据库结构
- `attendance/database.py`：数据库升级
- `attendance/templates/`：页面
- `attendance/translations/`：中文、英语和日语文字
- `attendance/static/`：样式和浏览器端文件
- `.github/workflows/`：自动测试和打包
