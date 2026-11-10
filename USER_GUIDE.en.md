<h1 align="center">📖 Attendance System User Guide</h1>

<h2 align="center"><a href="README.en.md">Back to downloads</a> ｜ <a href="USER_GUIDE.md">中文</a> ｜ <a href="USER_GUIDE.ja.md">日本語</a></h2>

For first-time use, sections 1 and 2 are all you need to start clocking. Read the rest when you need it.

## 1. Install and start

Download the package for your computer from the [download page](README.en.md), **extract it first**, then run the program inside. Nothing else needs to be installed.

- **Windows:** right-click the zip file, choose "Extract All", open the extracted folder and double-click the `.exe`.
- **macOS:** double-click the zip file, open the new folder, right-click the program and choose "Open".
- **Linux:** after extracting, run `chmod +x AttendanceSystem-*` and `./AttendanceSystem-*` in a terminal.

A program window appears and the browser opens by itself. The window shows the address on this computer (usually `http://127.0.0.1:5000`); type it into the browser if it did not open.

**Keep the program window open.** Closing it stops the system; closing only the browser does not. Employees, schedules and clock records are saved automatically and are still there next time.

If your computer shows a security prompt on first run, see section 13.

## 2. First-time setup

1. On the computer running the program, open Admin: `http://127.0.0.1:5000/admin/`
2. Go to "Employee management", click "Add employee", enter a name and save.
3. The page then shows that employee's **four-digit personal code**. Give it to the employee.
4. Back on the Admin home page, click "Clock-in QR code", print it and put it up in the workplace.

After these four steps, employees can clock in.

## 3. How employees clock in

1. Scan the QR code with a phone, or open the clock page on a shared computer or tablet at work.
2. Enter your personal code.
3. Tap "Check in" when you start and "Check out" when you finish.
4. Tap "Exit / Next person", or wait for the page to exit by itself.

Good to know:

- The phone must be on the same Wi-Fi as the computer running the program.
- The clock page shows only you, never other employees.
- You can clock in on a day without a shift; the time is recorded as usual.
- Five wrong codes in a row lock the entry for one minute, longer if it keeps happening (ten minutes at most).
- Finishing after midnight: a check-out before 5 a.m. is recorded on the previous day.

## 4. Employee management

Open "Admin → Employee management".

**Add an employee:** only the name is required. Choose "Regular employee" or "Part-time". Department and employee ID are optional; the ID is generated automatically.

- Regular employees work Monday to Friday by default.
- Part-time employees have no fixed days; they follow the generated schedule or simply their clock records.

**Weekly hours:** click "Weekly hours" next to an employee, tick the working days and set the times. A night shift can be entered as 22:00 to 06:00.

**Personal code:** if an employee forgets their code, click "Issue / reset personal code" and give them the new one. The old code stops working. Three-digit codes from older versions keep working until they are reset.

**Leaving:** click "Mark as left". The person can no longer clock in, all records are kept, and they still appear in that month's report. Only an employee with no attendance records (for example one added by mistake) can be deleted.

## 5. Corrections and leave

"Today's attendance" on the Admin home page lists who is in, who has not arrived, and who forgot to check out yesterday. Click "Fix" on a row to correct it directly.

You can also open "Correct clock records", choose the employee and date, then:

- **Add or change times:** enter the check-in and check-out times and click "Save".
- **Leave:** tick "Mark as leave" and click "Save". Leave does not count as an absence.

## 6. Reports and export

Open "Attendance reports", choose the dates (or click "This month" / "Last month") and click "Search".

- **Summary by employee:** one row per person with scheduled days, days worked, total hours, and the number of times late, left early, absent, on leave and without a check-out.
- **Daily detail:** one row per day. Click any row to correct that day.
- **Export:** "Export summary" gives one row per person, which suits payroll; "Export detail" gives one row per day. Both files open in Excel.

## 7. Availability and automatic scheduling (optional)

If you do not need rosters, skip this section; "Weekly hours" is enough.

**Employees submit availability:** open "Availability" at the top of the clock page, choose your name, enter your personal code, mark each day of next month as "Work", "Off" or "Either", and save.

**The administrator builds the schedule:** open "Automatic scheduling", set the minimum number of people per day, click "Generate schedule", check the result, adjust by hand if needed and save.

Once a schedule exists, **it decides whether that day is a working day**. Days without a schedule still follow the weekly hours.

## 8. Settings

Open "Admin → Settings".

**Attendance rules**

- Default working hours: used when a regular employee is added.
- Lunch break: by default 12:00 to 13:00 is not counted as working time. Untick it if you do not deduct lunch.
- Late grace period: 30 minutes by default. Clocking in within this time after the start is not late.

**Late-arrival email (optional)**

Enter the sending mailbox's server, port, account, app password and the address that should receive notices. When an employee is later than the set number of minutes, the administrator gets an email. The app password is created in the mailbox's own settings; the steps differ between email providers.

It is fine to leave this empty. The Admin home page also shows who has not arrived today.

## 9. Clock page styles

Open "Page styles". There are 12 to choose from. Click "Preview · Try clocking" to see one (a preview records nothing), then "Apply" when you like it. "Restore previous style" switches back.

| Style | Success animation |
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
| Tiny Planet | Starburst rings |

Changing the style does not change the clock address, the QR code or any attendance record. Pages that employees already have open switch to the new style within a few seconds.

## 10. Language

Choose 中文, English or 日本語 at the top of any Admin page. For the clock page, choose the language below the personal-code keypad.

## 11. Backup and restore

The system makes a backup every day, and also before an upgrade or before an employee is deleted. Backups are in the `backups` folder inside the data folder:

| System | Data folder |
| --- | --- |
| Windows | `%LOCALAPPDATA%\AttendanceSystem` |
| macOS | `~/Library/Application Support/AttendanceSystem` |
| Linux | `~/.local/share/attendance-system` |

Automatic backups are on the same computer as the data, so both are lost if the computer fails. About once a month, click "Back up and download now" on the Admin home page and keep the file on a USB drive or cloud storage.

**Restore:** close the program, rename `attendance.db` in the data folder to keep it, copy the backup file in and rename it to `attendance.db`, then start the program.

## 12. How attendance is calculated

- **Working days:** the generated schedule decides if there is one for that day; otherwise the weekly hours; otherwise it is a day off. Days before the employee was added do not count.
- **Hours:** check-out time minus check-in time, minus the lunch break.
- **Late:** checked in after the start time plus the grace period.
- **Left early:** checked out before the end time.
- **Absent:** a working day without any clock record.
- **No check-out:** checked in but not out. It shows "At work" on the day and "No check-out" from the next day; add the check-out time to fix it.
- **Leave:** not counted as an absence.
- **Clocking on a day off:** the time and hours are recorded; late and early are not judged.

## 13. Common questions

**Windows shows "Windows protected your PC"**
The program has no code-signing certificate, so Windows shows this prompt. Click "More info", then "Run anyway".

**Nothing happens when double-clicking on Windows**
Make sure you are running the program from the extracted folder, not from inside the zip file. If it still does not start, right-click the program, choose "Properties", tick "Unblock" at the bottom and try again.

**macOS says the developer cannot be verified, or the program will not open**
Right-click the program and choose "Open". If it is still blocked, go to "System Settings → Privacy & Security", click "Open Anyway", then right-click and "Open" once more.

**macOS says there is no application to open the file**
Open "Terminal", type `chmod +x ` (with a space at the end), drag the program into the Terminal window and press Return. Then drag the program into the window again and press Return. Keep the Terminal window open.

**The phone cannot open the page after scanning**
Check that the phone and the computer are on the same Wi-Fi and that the computer is on and not asleep. If the Admin home page shows a yellow notice that the network address has changed, print the QR code again. If the address changes often, ask whoever set up your network to give this computer a fixed address.

**The report shows an absence that should not be there**
Check whether that day is in the schedule, or ticked in the weekly hours. If the person did work but did not clock, add the record in "Correct clock records".

**A message says the system is already running**
The program is already open. Just open the address in your browser.

**The address is not 5000**
If another program is using 5000, the system picks another port. Use the address shown in the program window.

## 14. Where it can be used

- **Clocking in over the public internet is strictly forbidden.** Use the system only on the network inside your shop or office, and do not open it to the outside (port forwarding, tunnelling, hosting it in the cloud and so on). It is designed for in-store use; once it is reachable from outside, others could clock in as your staff or see employee information.
- **Admin opens only on the computer that runs the program.** There is no administrator password, so it is a good idea to set a login password on that computer.
- Clock records missed while away from the workplace are added by the administrator in Admin.
