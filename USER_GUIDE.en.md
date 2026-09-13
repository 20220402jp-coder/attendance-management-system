<h1 align="center">📖 Attendance System User Guide</h1>

<h2 align="center"><a href="README.en.md">Back to the download page</a></h2>

This guide explains each feature. For a new installation, complete the steps in order.

## 1. Windows: download, extract, start and stop

1. Download the Windows ZIP from the v1.0.2 GitHub release page.
2. Open Downloads, right-click the ZIP, choose “Extract All”, and click “Extract”.
3. Open the new folder and double-click the `.exe` inside. Do not run it from the ZIP preview or copy only the executable.
4. If Windows shows “Windows protected your PC”, confirm the file came from this release page, then choose “More info” → “Run anyway”.
5. Wait for the browser to open, or enter `http://127.0.0.1:5000/` manually. Keep the black program window open; close it to stop the system.

## 2. macOS: download, extract, start and stop

1. Choose macOS-arm64 for Apple silicon or macOS-x64 for Intel from the v1.0.2 release page.
2. Double-click the ZIP, open the extracted folder, and run the program inside.
3. If macOS blocks it, right-click and choose “Open”. If it remains blocked, use “System Settings → Privacy & Security → Open Anyway”, then right-click “Open” once more.
4. If macOS says there is no application to open it, use the Terminal method in section 16. Keep Terminal open while the system runs.

## 3. Linux: download, extract, start and stop

1. Download the Linux-x64 ZIP from the v1.0.2 release page.
2. Choose “Extract Here”, open the extracted folder, and run in a terminal:

```bash
chmod +x AttendanceSystem-*-Linux-x64
./AttendanceSystem-*-Linux-x64
```

3. Open `http://127.0.0.1:5000/` if the browser does not open automatically. Press `Ctrl+C` in the terminal to stop the system.

Employees, schedules and clock records are saved automatically. The downloads already include the required runtime.

## 4. First-time setup

1. On the GitHub v1.0.2 release page, download the ZIP matching your operating system and processor: Windows, macOS Apple silicon, macOS Intel, or Linux.
2. Extract it: right-click and choose “Extract All” on Windows, double-click the ZIP on macOS, or choose “Extract Here” on Linux. Open the new folder and run the program inside. Do not run it from the ZIP preview or copy only the executable.
3. Open `http://127.0.0.1:5000/admin/`.
2. Open “Employee Management”.
3. Add employees.
4. Set their work hours.
5. Create a schedule if needed.

## 5. Employee management

Open “Admin → Employee Management” to add, edit or delete employees. You can enter an employee ID, name, role or department, and preferred language. Use the schedule button beside an employee to set their working hours.

Check carefully before deleting an employee. A deleted employee can no longer clock in or out.

## 6. Check in and out

1. Select your name on the clock page.
2. Click “Check In” when work starts.
3. Click “Check Out” when work ends.

If several people clock at once, wait while the system processes them in order. After check-out, working time and attendance status are calculated automatically.

## 7. Submit preferred work dates

Open the availability page, select your name, and choose “Work”, “Off” or “Either” for each date. Save your choices when finished.

## 8. Create a schedule

Open “Admin → Automatic Scheduling”, set the number of people needed each day, generate the schedule, check the result, and adjust it if necessary. The schedule is used to determine lateness, early departure and absence.

## 9. Correct or add a clock record

Open “Admin → Correct Clock Records”, select an employee and date, search for the record, edit the check-in or check-out time, and save. Entering times for an empty date creates a new record.

## 10. Record leave

Open the clock correction page, select the employee and date, choose “Mark as leave”, and save. Leave appears in reports but is not counted as absence.

## 11. View attendance reports

Open “Admin → Attendance Reports”, select an employee and date range, and run the report. It shows attendance, scheduled days, hours, lateness, early departures, absences and leave. You can export the result as a table file.

## 12. Use a phone for clocking

Connect the computer and phone to the same network. Open “Clock-in QR Code” on the admin page and scan it with the phone. Use the print function if you want to display a printed QR code.

## 13. Set up late email notices

Open “Admin → Email Settings” and enter the mail server, port, sending account, app password, administrator email and reminder delay. Email setup is optional and does not affect other features.

## 14. Change the display language

Use the Chinese, English or Japanese switch at the top of any administration page. The system remembers the selected language.

## 15. How attendance is calculated

- Working time is check-out minus check-in, less any overlapping lunch break.
- Arriving after the scheduled start and grace period is late.
- Leaving before the scheduled end is an early departure.
- A scheduled day without a clock record is an absence.
- Approved leave is not counted as absence.
- A record with no check-out is shown as incomplete.

## 16. Common problems

### The page does not open automatically

Wait a few seconds, then enter `http://127.0.0.1:5000` in the browser.

### An employee is missing from the clock page

Confirm that the employee was added successfully, then refresh the clock page.

### The page says the system is already running

The program is already open. Find its program window and open `http://127.0.0.1:5000` in the browser.

### A report shows an absence unexpectedly

Check the schedule and the employee’s clock record. Correct the record if necessary.

### An employee forgot to check out

An administrator can add the check-out time on the clock correction page.

## 17. Choose a clock design (current source)

On the host computer, open `http://127.0.0.1:5000/admin/appearance`, or choose “Page styles” in Admin.

1. Select “Preview · Try clocking”, choose the demo employee and try the success animation. Preview does not change the global style or save attendance.
2. Return to Admin and select “Apply”. The selected design shows “Active” and applies to the whole system, not an individual employee.
3. “Restore previous style” restores only the design, not attendance data.
4. Switch Chinese, English or Japanese at the top. Names, descriptions, buttons, messages and previews follow that language.

| Design | Success animation |
| --- | --- |
| Original Classic | Confirmation sparkles |
| Neon Sci-Fi | Energy ring confirmation |
| Kimono Cartoon | Bowing girl |
| Aurora Voyage | Shooting star |
| Forest Breath | Unfolding leaves |
| Ocean Blues | Water ripples |
| Mountain Sunrise | Sunrise glow |
| Daily Ticket | Attendance stamp |
| Pixel Arcade | Bouncing coin |
| Candy Bubbles | Confetti burst |
| Minimal Monochrome | Drawing a checkmark |

The clock URL and QR code stay the same. New visits use the current design. Existing idle pages check about every 8 seconds, preload resources, then refresh while preserving employee selection and rechecking today's server state. Switching waits during submission, uncertain results or an open success dialog. This is a refresh at a safe point, not an instant in-place theme change.

Live success animations play only after server confirmation. Closing or replaying an animation does not submit another clock event. Wait while a disconnected request is being verified. The page falls back if 3D resources fail and supports reduced motion.

Refresh Admin if the page expires or another window changes the style. Phones can use the chosen clock design, but style management is restricted to the host computer.

## 18. Data, backups and demo records

| System | Default data directory |
| --- | --- |
| Windows | `%LOCALAPPDATA%\AttendanceSystem` |
| macOS | `~/Library/Application Support/AttendanceSystem` |
| Linux | `~/.local/share/attendance-system` |

This directory contains `attendance.db`, the application secret and logs. `ATTENDANCE_DATA_DIR`, when set, overrides this location.

Stop the app before copying the entire data directory for backup. Before restoring, back up the current directory, restore a backup for the same app version while stopped, then restart. A source-code backup does not include runtime data. Keep the database and secret private and out of public repositories.

New installations start empty. Style previews use a demo employee. Some local demo environments also contain historical records labelled “模拟” (simulated); these are not actual attendance and are not included in GitHub source or downloads. Keep demo departments separate when reviewing reports. There is no user-facing one-click two-month data generator.

## 19. Addresses and schedule rules

- Admin is `http://127.0.0.1:5000/admin/`. Normal startup and local shortcuts use `5000`, not the early demo port `5077`. Closing a browser tab does not stop the app; closing its program window does.
- On a phone, `127.0.0.1` means the phone itself. Use the QR code or the host computer's LAN IP with port `5000`; keep the host running and allow access through its firewall.
- **Attendance currently uses each employee's weekly working-hours table**, not the generated daily assignment table. Check weekly working hours and rest days after changing automatic assignments.
- Defaults are a 12:00–13:00 lunch break and 30-minute late grace period. Missing timestamps prevent a complete hours calculation. Time spent after the scheduled end is not automatically approved overtime.
- Full administrator accounts and permissions are not implemented. Local-only style management does not provide login protection for the entire Admin area.
