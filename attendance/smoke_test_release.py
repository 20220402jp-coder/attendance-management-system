"""启动打包成品，确认新安装可以正常使用。"""

import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')


BASE_URL = 'http://127.0.0.1:5000'
STARTUP_TIMEOUT_SECONDS = 90
EXPECTED_EMPTY_SETTINGS = {
    'smtp_server',
    'smtp_port',
    'smtp_user',
    'smtp_password',
    'admin_email',
    'email_from',
    'late_notify_minutes',
}


def find_executable():
    files = [path for path in Path('dist').iterdir() if path.is_file()]
    if len(files) != 1:
        raise RuntimeError(f'预期 dist 中只有一个程序，实际为: {files}')
    executable = files[0].resolve()
    if os.name != 'nt':
        executable.chmod(executable.stat().st_mode | 0o111)
    return executable


def request(path):
    with urllib.request.urlopen(BASE_URL + path, timeout=5) as response:
        body = response.read()
        if response.status != 200:
            raise RuntimeError(f'{path} 返回状态 {response.status}')
        return body


def wait_until_ready(process):
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_error = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'程序提前退出，退出码: {process.returncode}')
        try:
            info = json.loads(request('/api/server-info'))
            if info.get('ok'):
                return
        except (OSError, ValueError, urllib.error.URLError) as error:
            last_error = error
        time.sleep(1)
    raise RuntimeError(f'{STARTUP_TIMEOUT_SECONDS} 秒内未启动: {last_error}')


def check_database(data_dir):
    database = data_dir / 'attendance.db'
    if not database.is_file():
        raise RuntimeError('首次启动没有创建数据库')

    with sqlite3.connect(database) as connection:
        employee_count = connection.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
        record_count = connection.execute('SELECT COUNT(*) FROM attendance_records').fetchone()[0]
        settings = dict(connection.execute('SELECT key, value FROM settings'))

    if employee_count != 0 or record_count != 0:
        raise RuntimeError('新数据库中出现了测试员工或打卡记录')
    if set(settings) != EXPECTED_EMPTY_SETTINGS:
        raise RuntimeError(f'邮件配置项目不完整: {settings}')
    if any(settings.values()):
        raise RuntimeError('新数据库中的邮件配置不是空的')


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(
            ['taskkill', '/PID', str(process.pid), '/T', '/F'],
            capture_output=True,
            check=False,
        )
        process.wait(timeout=10)
        time.sleep(1)
    else:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main():
    executable = find_executable()
    with tempfile.TemporaryDirectory(
        prefix='attendance-release-check-',
        ignore_cleanup_errors=True,
    ) as temporary:
        temporary_path = Path(temporary)
        data_dir = temporary_path / 'data'
        log_dir = temporary_path / 'logs'
        environment = os.environ.copy()
        environment['ATTENDANCE_DATA_DIR'] = str(data_dir)
        environment['ATTENDANCE_LOG_DIR'] = str(log_dir)
        environment['PYTHONDONTWRITEBYTECODE'] = '1'

        process = subprocess.Popen(
            [str(executable)],
            cwd=temporary_path,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=os.name != 'nt',
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            ),
        )
        try:
            wait_until_ready(process)
            for path in ('/', '/admin/', '/admin/employees', '/admin/settings'):
                request(path)

            settings = json.loads(request('/api/settings'))
            if set(settings) != EXPECTED_EMPTY_SETTINGS or any(settings.values()):
                raise RuntimeError(f'邮件配置接口没有返回空配置: {settings}')

            check_database(data_dir)
            print(f'Packaged app smoke test passed: {executable.name}')
        except Exception:
            stop_process(process)
            output = process.stdout.read() if process.stdout else ''
            if output:
                print(output, file=sys.stderr)
            raise
        finally:
            stop_process(process)


if __name__ == '__main__':
    main()
