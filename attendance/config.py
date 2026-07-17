import os
import sys

# 运行模式判断
#   PyInstaller 打包后: sys._MEIPASS 是解压临时目录，数据文件放那
#   普通 python app.py: __file__ 就是脚本目录
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS  # 模板/翻译等数据文件
    DATA_DIR = os.path.dirname(sys.executable)  # 数据库/运行时文件放 exe 旁边
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BASE_DIR


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-to-a-random-secret')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(DATA_DIR, "attendance.db")}'
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
