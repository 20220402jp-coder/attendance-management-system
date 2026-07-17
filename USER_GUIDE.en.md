<h1 align="center">📖 Attendance System User Guide</h1>

<h2 align="center"><a href="README.en.md">Back to the download page</a></h2>

This guide explains each feature. For a new installation, complete the steps in order.

## 1. Start and stop

1. Double-click the unzipped program.
2. Wait for the browser to open automatically.
3. Close the program window when you want to stop the system.

Employees, schedules and clock records are saved automatically.

## 2. First-time setup

1. Open “Admin”.
2. Open “Employee Management”.
3. Add employees.
4. Set their work hours.
5. Create a schedule if needed.

## 3. Employee management

Open “Admin → Employee Management” to add, edit or delete employees. You can enter an employee ID, name, role or department, and preferred language. Use the schedule button beside an employee to set their working hours.

Check carefully before deleting an employee. A deleted employee can no longer clock in or out.

## 4. Check in and out

1. Select your name on the clock page.
2. Click “Check In” when work starts.
3. Click “Check Out” when work ends.

If several people clock at once, wait while the system processes them in order. After check-out, working time and attendance status are calculated automatically.

## 5. Submit preferred work dates

Open the availability page, select your name, and choose “Work”, “Off” or “Either” for each date. Save your choices when finished.

## 6. Create a schedule

Open “Admin → Automatic Scheduling”, set the number of people needed each day, generate the schedule, check the result, and adjust it if necessary. The schedule is used to determine lateness, early departure and absence.

## 7. Correct or add a clock record

Open “Admin → Correct Clock Records”, select an employee and date, search for the record, edit the check-in or check-out time, and save. Entering times for an empty date creates a new record.

## 8. Record leave

Open the clock correction page, select the employee and date, choose “Mark as leave”, and save. Leave appears in reports but is not counted as absence.

## 9. View attendance reports

Open “Admin → Attendance Reports”, select an employee and date range, and run the report. It shows attendance, scheduled days, hours, lateness, early departures, absences and leave. You can export the result as a table file.

## 10. Use a phone for clocking

Connect the computer and phone to the same network. Open “Clock-in QR Code” on the admin page and scan it with the phone. Use the print function if you want to display a printed QR code.

## 11. Set up late email notices

Open “Admin → Email Settings” and enter the mail server, port, sending account, app password, administrator email and reminder delay. Email setup is optional and does not affect other features.

## 12. Change the display language

Use the Chinese, English or Japanese switch at the top of any administration page. The system remembers the selected language.

## 13. How attendance is calculated

- Working time is check-out minus check-in, less any overlapping lunch break.
- Arriving after the scheduled start and grace period is late.
- Leaving before the scheduled end is an early departure.
- A scheduled day without a clock record is an absence.
- Approved leave is not counted as absence.
- A record with no check-out is shown as incomplete.

## 14. Common problems

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
