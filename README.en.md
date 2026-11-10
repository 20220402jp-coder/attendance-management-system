<h1 align="center">📋 Attendance System</h1>

<h2 align="center"><a href="README.md">中文</a> ｜ <a href="README.ja.md">日本語</a> ｜ English</h2>

An attendance clock for small shops and small companies. It runs on one computer at your workplace and employees clock in by scanning a QR code with their phones. No computer skills and no online sign-up are needed. Available in Chinese, Japanese and English.

## What it does

- **Clocking:** employees scan the code, enter their personal code and tap check in or check out.
- **Today's attendance:** the Admin home page shows who is in, who has not arrived and who forgot to check out yesterday.
- **Corrections and leave:** fix any day's record in one click.
- **Reports and export:** days worked, hours, and times late or left early for each person, exportable for payroll in Excel.
- **Scheduling (optional):** employees submit the days they would like to work and the system builds next month's schedule.
- **12 clock page styles:** from a classic clock to the 3D "Tiny Planet", each with its own success animation, switchable in Admin.
- **Automatic backups:** data is backed up every day, and you can download a copy at any time.

<h1>Download</h1>

<h2>🪟 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.4/AttendanceSystem-1.0.4-Windows-x64.exe.zip">Download for Windows</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.4/AttendanceSystem-1.0.4-macOS-arm64.zip">Download for Mac (M1, M2, M3 or M4)</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.4/AttendanceSystem-1.0.4-macOS-x64.zip">Download for an Intel Mac</a></h2>

<h2>🐧 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.0.4/AttendanceSystem-1.0.4-Linux-x64.zip">Download for Linux</a></h2>

The current download is v1.0.4. This page and the user guide describe the latest source code; some features arrive with the next release. See the [Changelog](CHANGELOG.md) for the differences.

<h1>How to use it</h1>

<h2>1. Download and extract</h2>

Download only the one file that matches your computer. It is a zip file, so **extract it before running**:

- Windows: right-click the zip file and choose "Extract All".
- Mac: double-click the zip file.
- Linux: right-click the zip file and choose "Extract Here".

<h2>2. Start the program</h2>

Open the extracted folder and double-click the `AttendanceSystem-...` program inside (on a Mac, right-click it and choose "Open"). After a few seconds a program window appears and the browser opens by itself.

Keep the program window open. Closing it stops the system.

Your computer may show a security prompt the first time:

- **Windows** shows "Windows protected your PC": click "More info", then "Run anyway".
- **Mac** says the developer cannot be verified: go to "System Settings → Privacy & Security", click "Open Anyway", then right-click the program and choose "Open".

For other start-up problems, see [Common questions in the user guide](USER_GUIDE.en.md#13-common-questions).

<h2>3. Add employees and print the QR code</h2>

1. On this computer, open Admin: `http://127.0.0.1:5000/admin/`
2. Go to "Employee management" and add an employee. Only a name is needed. After saving, the employee's four-digit personal code is shown; give it to the employee.
3. Back on the Admin home page, click "Clock-in QR code", print it and put it up at your workplace.

Employees can now scan the code, enter their personal code and clock in. Their phones must be on the same Wi-Fi as this computer.

## Where it can be used

- **Clocking in over the public internet is strictly forbidden.** Use the system only on the network inside your shop or office, and do not open it to the outside (port forwarding, tunnelling, hosting it in the cloud and so on).
- **Admin opens only on the computer that runs the program.** Phones and other computers can only clock in and submit availability.
- Clock records missed while away from the workplace are added by the administrator in Admin.

<h2>📖 <a href="USER_GUIDE.en.md">Open the full user guide</a></h2>

For development and packaging, see [DEVELOPMENT.md](DEVELOPMENT.md).
