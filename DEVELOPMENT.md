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

这里保存数据库、程序密钥、日志和 `backups/` 备份，不会随源代码上传或打进安装包。

## 测试

```bash
cd attendance
python -m pytest -q ../tests
```

每次修改后都应运行测试并实际启动程序，确认首页和管理页面可以打开。

打包完成后运行成品启动检查：

```bash
cd attendance
python smoke_test_release.py
```

它会在临时空目录中启动打包成品，检查主要页面、空数据库和空邮件配置，然后关闭程序。GitHub 在四种系统上全部通过这项检查后，才会压缩或发布文件。

## 打包

推送普通代码不会自动打包。创建版本标签后，GitHub 会分别生成 Windows、macOS 和 Linux 程序。

本地打包命令：

```bash
cd attendance
python build.py
```

## 主要文件

- `attendance/app.py`：页面和主要功能
- `attendance/rules.py`：考勤规则（应出勤判定、状态、工时），所有页面共用
- `attendance/backup.py`：数据库备份
- `attendance/models.py`：数据库结构
- `attendance/database.py`：数据库升级
- `attendance/templates/`：页面
- `attendance/translations/`：中文、英语和日语文字
- `attendance/static/`：样式和浏览器端文件
- `.github/workflows/`：自动测试和打包

## 访问范围

`app.py` 的 `admin_is_local_only` 默认拒绝所有非本机请求，只有 `PUBLIC_EXACT` 和
`PUBLIC_PREFIXES` 列出的打卡、报班地址对局域网开放。新增管理页面或接口时不需要额外处理；
新增员工要用的地址时必须加进这两个列表，并在 `tests/test_admin_hardening.py` 里补上断言。

## 提交规范

- 从 `main` 拉分支（`fix/…`、`feat/…`、`docs/…`），通过 Pull Request 合并，不直接推送 `main`。
- 提交信息使用 Conventional Commits：`fix(attendance): …`、`feat(admin): …`、`docs: …`。
- 对使用者有影响的改动写进 `CHANGELOG.md` 的「下一个版本」一节，中文、日文、英文三部分都要写。
- `README` 和 `USER_GUIDE` 各有三种语言，结构保持一致；改一份就要同步另外两份。
- 三种语言的翻译键必须一致（`tests/test_i18n.py` 会检查）。
