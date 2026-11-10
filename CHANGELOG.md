# 更新记录 ｜ 更新履歴 ｜ Changelog

[中文](#中文) ｜ [日本語](#日本語) ｜ [English](#english)

---

## 中文

### 1.1.0

**修好的问题**

- 新建的员工在周一到周五打不了卡。现在正式员工默认周一到周五上班；已有的员工在升级时自动修正。
- 统计把休息日、入职之前的日子算成了缺勤。
- 忘记签退、收到迟到邮件后一直没来的员工，在统计里显示成了「正常」。
- 兼职的工时在导出时被截成整数（7.9 小时变成 7 小时），现在保留两位小数。
- 工号重复时只提示「保存失败」，现在会说明原因。
- 打开邮件设置页时不显示已保存的内容，再点保存会把设置清空。

**新功能**

- 后台首页「今日出勤」：今天谁到了、谁没到、昨天谁忘了签退，点一下就能补卡。
- 统计页新增按人汇总，可以单独导出；点每日明细的任意一行可以直接修改。
- 可以设置默认上下班时间、午休（可以关闭）和迟到宽限。
- 排好班的日子，按排班结果判断是否应出勤。
- 没有排班的日子也可以打卡。
- 过了半夜才下班的，凌晨 5 点前签退会记到前一天；也可以设置跨夜班次。
- 添加员工只需要填姓名，工号和个人码自动生成。
- 员工可以「设为离职」，考勤记录全部保留。
- 新的「每周班次」设置：勾选上班的日子并填写时间。
- 每天自动备份，后台可以一键下载备份。
- 电脑的网络地址变了、二维码失效时，后台首页会提醒重新打印。
- 5000 端口被占用时自动换端口。
- 新增 3D 打卡样式「小小星球」。

**有变化的地方**

- 管理后台只能在运行程序的那台电脑上打开。手机和其他电脑只能打卡和报班。
- 个人码改为四位。以前发的三位码可以继续用，重置后变成四位。
- 个人码输错 5 次后锁 1 分钟（以前是 10 分钟），继续输错会逐步加长，最长 10 分钟。
- 有考勤记录的员工不能删除，请改用「设为离职」。
- 「邮件」页改名为「设置」，迟到邮件提醒仍然可用。
- 以前生成过的排班结果，升级后会开始影响「哪天算应出勤」。

**还没做的**

- 双击即用、不显示程序窗口、开机自动启动的安装包。

### 1.0.4

- 全部打卡样式支持中文、日文、英文。

---

## 日本語

### 1.1.0

**修正した問題**

- 新しく登録した従業員が月曜から金曜に打刻できませんでした。正社員の初期設定を月曜〜金曜の出勤に改め、登録済みの従業員はバージョンアップ時に自動で修正します。
- 休みの日や、登録日より前の日が、集計で欠勤になっていました。
- 退勤を打刻し忘れた日や、遅刻メールの送信後に出勤しなかった日が、集計で「正常」になっていました。
- パートの労働時間がエクスポート時に切り捨てられていました（7.9時間が7時間）。小数第2位まで出力します。
- 社員番号が重複したとき「保存できませんでした」としか表示されませんでした。理由を表示します。
- メール設定の画面を開くと保存済みの内容が表示されず、そのまま保存すると設定が消えていました。

**新しい機能**

- 管理画面トップの「本日の出勤」：出勤済みの人、まだ来ていない人、昨日退勤を打刻し忘れた人を表示し、その場で修正できます。
- 集計に従業員別の集計を追加し、単独でエクスポートできます。日別の明細は行を押すと修正できます。
- 標準の勤務時間、昼休み（オフにできます）、遅刻の猶予を設定できます。
- シフト表のある日は、シフト表で出勤日かどうかを判断します。
- シフトのない日でも打刻できます。
- 退勤が深夜0時を過ぎた場合、午前5時までの退勤は前日の記録になります。夜勤のシフトも設定できます。
- 従業員の追加は氏名だけで済みます。社員番号と個人コードは自動で付きます。
- 従業員を「退職にする」ことができ、勤怠記録はすべて残ります。
- 新しい「週の勤務時間」の設定：出勤する曜日にチェックを入れて時間を入力します。
- 毎日自動でバックアップし、管理画面からワンクリックでダウンロードできます。
- パソコンのネットワークアドレスが変わって QR コードが使えなくなると、管理画面のトップでお知らせします。
- ポート 5000 が使用中の場合は、別のポートを自動で使います。
- 3Dの打刻画面「ちいさな星」を追加しました。

**変更点**

- 管理画面は、プログラムを実行しているパソコンでだけ開けます。スマートフォンやほかのパソコンでできるのは、打刻とシフト希望の提出だけです。
- 個人コードは4桁になりました。これまでの3桁のコードは引き続き使え、リセットすると4桁になります。
- 個人コードを5回間違えたときのロックは1分になりました（以前は10分）。続けて間違えると少しずつ長くなり、最長10分です。
- 勤怠記録のある従業員は削除できません。「退職にする」を使ってください。
- 「メール」の画面は「設定」に名前が変わりました。遅刻メール通知は引き続き使えます。
- 以前に作成したシフト表が、バージョンアップ後は「出勤日かどうか」の判断に使われるようになります。

**まだ対応していないこと**

- ダブルクリックだけで使え、プログラムのウィンドウを表示せず、パソコンの起動時に自動で始まるインストーラー。

### 1.0.4

- すべての打刻画面が中国語・日本語・英語に対応しました。

---

## English

### 1.1.0

**Fixed**

- Newly added employees could not clock in from Monday to Friday. Regular employees now work Monday to Friday by default, and existing employees are corrected automatically on upgrade.
- Days off and days before an employee was added were reported as absences.
- A forgotten check-out, or a no-show after a late-arrival email, was reported as "Normal".
- Part-time hours were cut down to whole numbers in exports (7.9 hours became 7). They now keep two decimals.
- A duplicate employee ID only said "Could not save". The reason is now shown.
- The email settings page did not show the saved values, and saving again cleared them.

**New**

- "Today's attendance" on the Admin home page: who is in, who has not arrived and who forgot to check out yesterday, each with a one-click fix.
- A summary by employee in Reports, with its own export. Click any row of the daily detail to correct that day.
- Default working hours, the lunch break (which can be switched off) and the late grace period can be set.
- On days with a generated schedule, the schedule decides whether it is a working day.
- Clocking in works on days without a shift.
- When work ends after midnight, a check-out before 5 a.m. is recorded on the previous day. Overnight shifts can also be set.
- Adding an employee needs only a name. The employee ID and personal code are generated.
- Employees can be marked as left, keeping all their records.
- New "Weekly hours" setting: tick the working days and set the times.
- A backup every day, and a one-click backup download in Admin.
- When the computer's network address changes and the QR code stops working, the Admin home page reminds you to print it again.
- If port 5000 is in use, another port is chosen automatically.
- New 3D clock style "Tiny Planet".

**Changed**

- Admin opens only on the computer that runs the program. Phones and other computers can only clock in and submit availability.
- Personal codes are now four digits. Existing three-digit codes keep working and become four digits when reset.
- Five wrong codes lock the entry for one minute (previously ten). The lock grows if it keeps happening, up to ten minutes.
- Employees with attendance records cannot be deleted. Use "Mark as left" instead.
- The "Email" page is now "Settings". Late-arrival emails still work as before.
- Schedules generated in earlier versions start to affect which days count as working days after the upgrade.

**Not done yet**

- An installer that starts with a double-click, shows no program window and launches when the computer starts.

### 1.0.4

- All clock styles are available in Chinese, Japanese and English.

---

更早的版本 ｜ 以前のバージョン ｜ Earlier versions: [GitHub Releases](https://github.com/20220402jp-coder/attendance-management-system/releases)
