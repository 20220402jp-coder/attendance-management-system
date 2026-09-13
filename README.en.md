<h1 align="center">📋 Attendance Management System</h1>

<h2 align="center"><a href="README.md">中文</a> ｜ <a href="README.ja.md">日本語</a> ｜ English</h2>

This system is made for small businesses that need a simple attendance and shift management tool. It supports Chinese, English and Japanese.

## Current version and features

The published download is **v1.0.4**, including personal-code availability, QR-code clock-in, and access-control updates.

- Employee management, weekly working hours, availability, automatic scheduling, attendance corrections and report export.
- **11 selectable clock designs**, including the original page. Every design has a success animation.
- Preview, apply and restore the previous design from Admin, while keeping the same employee clock URL.
- Chinese, English and Japanese style management, with previews following the selected language.

## Addresses

While the app is running, open these on its host computer:

| Page | Address |
| --- | --- |
| Clock | http://127.0.0.1:5000/ |
| Admin | http://127.0.0.1:5000/admin/ |
| Page styles (current source) | http://127.0.0.1:5000/admin/appearance |

`5077` was an early demo port. Normal startup uses `5000`. Open the Admin address directly if there is no Admin link. If a desktop shortcut has been created locally, you can use it; the repository does not automatically install desktop shortcuts.

Style settings can currently be managed only on the host computer. A complete administrator login and permission system is not implemented; use a trusted network. See the [User guide](USER_GUIDE.en.md) for switching, mobile access and backups.

<h1>Download</h1>

<h2>🪟 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.4/AttendanceSystem-1.0.4-Windows-x64.exe.zip">Download for Windows</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.4/AttendanceSystem-1.0.4-macOS-arm64.zip">Download for Mac (M1, M2, M3 or M4)</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.4/AttendanceSystem-1.0.4-macOS-x64.zip">Download for an Intel Mac</a></h2>

<h2>🐧 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.4/AttendanceSystem-1.0.4-Linux-x64.zip">Download for Linux</a></h2>

<h1>How to use it</h1>

<h2>1. Download the file for your computer</h2>

<h2>2. Unzip the downloaded file</h2>

Choose the ZIP for your operating system and processor. Extract it, then open the new folder and run the program inside. On Windows, right-click the ZIP and choose “Extract All”; on macOS, double-click the ZIP; on Linux, choose “Extract Here”. Do not run the program from the ZIP preview or copy only the executable.

<h2>3. Double-click the program inside</h2>

The program opens a web page automatically. The first time you use it, open “Admin → Employee Management” and add your employees. Close the program window to stop the system.

### If Windows shows a security warning

Confirm the file came from this project's GitHub release page, then click “More info” → “Run anyway”. If “More info” is not shown, download the file again from the release page. A black program window must stay open while the system is running.

### If the program will not open on a Mac

Right-click the program and choose “Open”. If it is still blocked, open “System Settings → Privacy & Security” and click “Open Anyway”.

### If the program will not start by double-clicking on Linux

```bash
chmod +x AttendanceSystem-*-Linux-*
```

You do not need to install Python or any other software.

<h2>📖 <a href="USER_GUIDE.en.md">Open the complete user guide</a></h2>
