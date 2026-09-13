<h1 align="center">📋 考勤打卡系统</h1>

<h2 align="center">中文 ｜ <a href="README.ja.md">日本語</a> ｜ <a href="README.en.md">English</a></h2>
这是为需要简单考勤和排班工具的小企业制作的系统，支持中文、英文和日文
## 当前版本与功能

已发布下载包为 **v1.0.2**，包含近期的个人码报班、扫码打卡和权限改动。

- 员工管理、每周工作时间、报班意向、自动排班、打卡修正及统计导出。
- **11 款可选打卡页面**，保留经典原版；每款均有打卡成功动画。
- 后台可预览、应用样式并恢复上一款，员工继续使用同一个打卡地址。
- 页面样式管理支持中文、英文、日文，预览跟随当前语言。

## 常用入口

程序运行期间，在运行程序的电脑上打开：

| 页面 | 地址 |
| --- | --- |
| 员工打卡 | http://127.0.0.1:5000/ |
| 管理后台 | http://127.0.0.1:5000/admin/ |
| 页面样式（最新源码） | http://127.0.0.1:5000/admin/appearance |

`5077` 是早期演示使用的端口，正式启动入口使用 `5000`。没有看到「管理」链接时，可直接打开上表中的后台地址。本机若已创建“考勤管理系统”快捷方式，也可双击启动；仓库不会自动为所有电脑安装桌面快捷方式。

页面样式设置目前仅允许在运行程序的电脑上管理。系统尚无完整管理员登录和权限体系，请在可信网络内使用；详细操作、手机访问及备份方法见 [使用说明](USER_GUIDE.md)。

<h1>下载程序</h1>

<h2>🪟 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.2/AttendanceSystem-1.0.2-Windows-x64.exe.zip">Windows 电脑点这里下载</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.2/AttendanceSystem-1.0.2-macOS-arm64.zip">Mac 电脑点这里下载（M1、M2、M3、M4 芯片）</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.2/AttendanceSystem-1.0.2-macOS-x64.zip">Intel 芯片的 Mac 点这里下载</a></h2>

<h2>🐧 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.2/AttendanceSystem-1.0.2-Linux-x64.zip">Linux 电脑点这里下载</a></h2>



<h1>怎么使用</h1>

<h2>1. 下载对应的文件</h2>

在 [v1.0.2 发布页](https://github.com/20220402jp-coder/attendance-management-system/releases/tag/v1.0.2) 中，只下载与电脑系统和芯片相符的一个文件。下载的是 `.zip` 压缩包，不要直接在压缩包里运行程序。

<h2>2. 解压缩</h2>

- Windows：打开「下载」文件夹，右键 `AttendanceSystem-...-Windows-x64.exe.zip`，选择「全部解压缩」，确认目标文件夹后点击「解压缩」。解压完成后打开新文件夹，双击里面的 `.exe` 程序。不要在压缩包预览窗口中双击，也不要只把 `.exe` 拖到桌面运行。
- macOS：在「下载」文件夹中双击 `.zip` 文件，Finder 会生成一个同名文件夹。
- Linux：右键文件，选择「解压到此处」或「Extract Here」。

解压完成后，程序必须放在一个不会自动清理的文件夹中。不要只把程序拖出来运行，也不要删除同一文件夹里的其他文件。

<h2>3. 启动程序</h2>

打开解压后的文件夹，双击里面唯一的 `AttendanceSystem-...` 程序。稍等几秒，浏览器会自动打开打卡页面。浏览器没有自动打开时，手动输入 `http://127.0.0.1:5000/`。

第一次使用时，打开「管理 → 员工管理」添加员工，然后为每名员工生成三位个人码。关闭程序窗口即可停止系统；只关闭浏览器页面不会停止程序。

### Windows 如果出现安全提醒

首次运行可能出现蓝色窗口「Windows 已保护你的电脑」。先确认文件名以 `Windows-x64.exe` 结尾并且来自本项目 GitHub 发布页，再点击「更多信息」，最后点击「仍要运行」。这是下载程序没有购买商业代码签名证书时的常见提示，不代表程序缺少运行文件。如果窗口中没有「更多信息」，关闭提示并重新从发布页下载，不要使用来历不明的文件。

如果双击后没有反应：确认程序仍在解压后的文件夹中，右键 `.exe` 选择「以管理员身份运行」；若公司电脑禁止运行，请联系电脑管理员。程序启动后会出现一个黑色运行窗口，这个窗口不能关闭，关闭它会停止考勤系统。

### Mac 如果无法打开

这个下载包是命令行程序，不是带图标的 `.app` 应用，所以 macOS 有时会提示「没有对应的打开程序」。请按下面顺序处理：

1. 在 Finder 中右键点击程序，选择「打开」，再确认「打开」。
2. 如果提示无法验证开发者或存在安全风险，打开「系统设置 → 隐私与安全性」，在下方点击「仍要打开」，然后再回到程序上右键选择「打开」。
3. 如果双击仍提示没有打开程序，打开「终端」，输入 `cd `（末尾有一个空格），再把程序文件拖进终端窗口，按回车；随后输入 `chmod +x `，再次把程序拖进终端，按回车；最后输入 `./`，把程序拖进终端，按回车。终端窗口需要保持打开，关闭它会停止系统。

只有确认文件来自本项目发布页时，才按上述步骤允许打开；不要对来源不明的程序绕过安全提示。

### Linux 如果无法双击运行

```bash
unzip AttendanceSystem-*-Linux-*.zip
chmod +x AttendanceSystem-*-Linux-x64
./AttendanceSystem-*-Linux-x64
```

本程序不需要安装 Python 或其他软件。

<h2>📖 <a href="USER_GUIDE.md">点这里打开完整使用说明</a></h2>
