"""创建空数据库和数据表（在项目目录下直接运行）。

用法: python init_db.py
如果数据库已存在，只补齐缺少的表，不修改已有数据。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, first_run_setup

with app.app_context():
    first_run_setup()
