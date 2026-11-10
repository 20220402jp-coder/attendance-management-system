"""数据库备份：自动每日一份，重要改动前一份，后台可手动下载。"""

import sqlite3
from datetime import date, datetime
from importlib import import_module

KEEP_AUTO = 60  # 自动备份最多保留的份数；手动和升级前的备份不自动清理


def _paths():
    config = import_module('config')
    return config.DATABASE_PATH, config.DATA_PATH / 'backups'


def make_backup(reason='manual'):
    """用 SQLite 在线备份生成一份完整副本，返回文件路径；没有数据库时返回 None。"""
    database, folder = _paths()
    if not database.exists():
        return None
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    target = folder / f'attendance-{stamp}-{reason}.db'
    index = 1
    while target.exists():
        index += 1
        target = folder / f'attendance-{stamp}-{reason}-{index}.db'
    source = sqlite3.connect(database)
    destination = sqlite3.connect(target)
    try:
        with destination:
            source.backup(destination)
    finally:
        destination.close()
        source.close()
    _prune(folder)
    return target


def _prune(folder):
    automatic = sorted(folder.glob('attendance-*-auto*.db'))
    for old in automatic[:-KEEP_AUTO]:
        try:
            old.unlink()
        except OSError:
            pass


def last_backup_time():
    _, folder = _paths()
    if not folder.exists():
        return None
    files = list(folder.glob('attendance-*.db'))
    if not files:
        return None
    return datetime.fromtimestamp(max(item.stat().st_mtime for item in files))


def backup_if_due():
    """今天还没有任何备份时自动备份一次。"""
    latest = last_backup_time()
    if latest and latest.date() == date.today():
        return None
    return make_backup('auto')
