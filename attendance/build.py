"""在当前操作系统生成独立可执行程序。"""

import os
import platform
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from version import APP_VERSION


def create_icon():
    """生成简洁的考勤日历图标，供各系统打包使用。"""
    output = Path('build') / 'attendance-icon.png'
    output.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((48, 72, 464, 464), radius=72, fill='#2563eb')
    draw.rounded_rectangle((88, 144, 424, 416), radius=32, fill='white')
    draw.rectangle((48, 144, 464, 208), fill='#1d4ed8')
    draw.rounded_rectangle((128, 40, 176, 136), radius=20, fill='#93c5fd')
    draw.rounded_rectangle((336, 40, 384, 136), radius=20, fill='#93c5fd')
    draw.line((152, 304, 224, 360, 368, 248), fill='#16a34a', width=40, joint='curve')
    image.save(output)
    return str(output)


system_name = {'Darwin': 'macOS', 'Windows': 'Windows', 'Linux': 'Linux'}[platform.system()]
machine = platform.machine().lower().replace('x86_64', 'x64').replace('amd64', 'x64')
name = f'AttendanceSystem-{APP_VERSION}-{system_name}-{machine}'
icon = create_icon()

command = [
    sys.executable, '-m', 'PyInstaller',
    '--noconfirm', '--clean', '--onefile', '--console',
    '--name', name,
    '--icon', icon,
    '--add-data', f'templates{os.pathsep}templates',
    '--add-data', f'translations{os.pathsep}translations',
    '--add-data', f'static{os.pathsep}static',
    '--hidden-import', 'flask_sqlalchemy',
    'app.py',
]
subprocess.run(command, check=True)
print(os.path.join('dist', name + ('.exe' if platform.system() == 'Windows' else '')))
