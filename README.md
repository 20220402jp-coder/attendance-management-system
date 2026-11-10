<h1 align="center">📋 考勤打卡系统</h1>

<h2 align="center">中文 ｜ <a href="README.ja.md">日本語</a> ｜ <a href="README.en.md">English</a></h2>

给小店铺、小公司用的考勤打卡工具。在店里的一台电脑上运行，员工用手机扫码打卡，不需要懂电脑，也不需要联网注册。支持中文、日文、英文。

## 能做什么

- **打卡：** 员工扫码后输入自己的个人码，点一下签到或签退。
- **今日出勤：** 后台首页直接看到今天谁到了、谁没到、昨天谁忘了签退。
- **补卡和请假：** 点一下就能修改某一天的记录。
- **统计和导出：** 每人的出勤天数、工时、迟到早退次数，可导出给 Excel 算工资。
- **排班（可选）：** 员工提交希望上班的日期，系统自动排出下个月的班表。
- **12 款打卡页面：** 从经典时钟到 3D「小小星球」，每款都有打卡成功动画，后台一键切换。
- **自动备份：** 每天自动备份数据，也可以随时下载一份另存。

<h1>下载程序</h1>

<h2>🪟 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.1.0/AttendanceSystem-1.1.0-Windows-x64.exe.zip">Windows 电脑点这里下载</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.1.0/AttendanceSystem-1.1.0-macOS-arm64.zip">Mac 电脑点这里下载（M1、M2、M3、M4 芯片）</a></h2>

<h2>🍎 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.1.0/AttendanceSystem-1.1.0-macOS-x64.zip">Intel 芯片的 Mac 点这里下载</a></h2>

<h2>🐧 <a href="https://github.com/20220402jp-coder/attendance-management-system/releases/download/v1.1.0/AttendanceSystem-1.1.0-Linux-x64.zip">Linux 电脑点这里下载</a></h2>

当前版本是 v1.1.0，改动见[更新记录](CHANGELOG.md)。从旧版本升级时，直接用新程序替换旧程序即可，数据会保留并自动升级。

<h1>怎么使用</h1>

<h2>1. 下载并解压</h2>

只下载与自己电脑对应的那一个文件。下载的是压缩包，**要先解压再运行**：

- Windows：右键压缩包，选择「全部解压缩」。
- Mac：双击压缩包。
- Linux：右键压缩包，选择「解压到此处」。

<h2>2. 启动程序</h2>

打开解压后的文件夹，双击里面的 `AttendanceSystem-...` 程序（Mac 请右键选择「打开」）。稍等几秒，会出现一个程序窗口，浏览器随即自动打开。

程序窗口要一直开着，关掉它系统就停止了。

第一次运行时电脑可能弹出安全提示：

- **Windows** 提示「Windows 已保护你的电脑」：点「更多信息」，再点「仍要运行」。
- **Mac** 提示无法验证开发者：到「系统设置 → 隐私与安全性」点「仍要打开」，再右键程序选择「打开」。

其他启动问题见[使用说明的常见问题](USER_GUIDE.md#13-常见问题)。

<h2>3. 添加员工，打印二维码</h2>

1. 在这台电脑上打开管理后台：`http://127.0.0.1:5000/admin/`
2. 进入「员工管理」添加员工，只需要填姓名。保存后会显示这名员工的四位个人码，把它告诉本人。
3. 回到后台首页，点「打卡二维码」，打印出来贴在店里。

之后员工用手机扫码、输入个人码就能打卡。手机要和这台电脑连同一个 Wi-Fi。

## 使用范围

- **严禁通过公网打卡。** 本系统只能在店内或办公室的同一个网络里使用，请不要把它开放到外网（端口映射、内网穿透、放到云服务器等）。
- **管理后台只能在运行程序的这台电脑上打开**，手机和其他电脑只能打卡和报班。
- 员工在店外漏打的卡，由管理员在后台补。

<h2>📖 <a href="USER_GUIDE.md">点这里打开完整使用说明</a></h2>

开发和打包方法见 [DEVELOPMENT.md](DEVELOPMENT.md)。
