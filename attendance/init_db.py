"""初始化数据库（在项目目录下直接运行）。

用法: python init_db.py
如果数据库已存在则跳过。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, first_run_setup

with app.app_context():
    first_run_setup()
