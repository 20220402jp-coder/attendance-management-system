import os
import secrets
import sys
from pathlib import Path

# 模板、翻译和静态文件始终跟随程序。
if getattr(sys, 'frozen', False):
    BASE_DIR = str(Path(sys._MEIPASS))
else:
    BASE_DIR = str(Path(__file__).resolve().parent)


def _user_data_dir():
    """返回当前操作系统的正式用户数据目录。"""
    override = os.environ.get('ATTENDANCE_DATA_DIR')
    if override:
        path = Path(override).expanduser()
    elif sys.platform == 'win32':
        root = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA')
        path = Path(root) / 'AttendanceSystem' if root else Path.home() / 'AppData' / 'Local' / 'AttendanceSystem'
    elif sys.platform == 'darwin':
        path = Path.home() / 'Library' / 'Application Support' / 'AttendanceSystem'
    else:
        root = os.environ.get('XDG_DATA_HOME')
        path = Path(root).expanduser() / 'attendance-system' if root else Path.home() / '.local' / 'share' / 'attendance-system'

    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _secret_key(data_dir):
    """从环境变量读取密钥，或在用户数据目录持久化生成。"""
    configured = os.environ.get('SECRET_KEY')
    if configured:
        return configured

    key_path = data_dir / 'secret_key'
    if key_path.exists():
        return key_path.read_text(encoding='utf-8').strip()

    key = secrets.token_urlsafe(48)
    key_path.write_text(key, encoding='utf-8')
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    return key


DATA_PATH = _user_data_dir()
DATA_DIR = str(DATA_PATH)
DATABASE_PATH = DATA_PATH / 'attendance.db'


class Config:
    SECRET_KEY = _secret_key(DATA_PATH)
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH.as_posix()}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Lunch break (12:00 - 13:00)
    LUNCH_START = '12:00'
    LUNCH_END   = '13:00'

    # Grace period for status (minutes)
    GRACE_PERIOD = 30

    # Late notification (send email after X minutes past start time)
    LATE_NOTIFY_MINUTES = 10
    LATE_CHECK_INTERVAL = 60  # background check every 60 seconds

    # Email SMTP settings (set via env vars)
    SMTP_SERVER   = os.environ.get('SMTP_SERVER', '')
    SMTP_PORT     = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USER     = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    ADMIN_EMAIL   = os.environ.get('ADMIN_EMAIL', '')
    EMAIL_FROM    = os.environ.get('EMAIL_FROM', 'attendance@local')
