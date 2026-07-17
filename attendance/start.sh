#!/usr/bin/env bash
# 考勤系统启动脚本
cd "$(dirname "$0")"

VENV_DIR="${ATTENDANCE_VENV_DIR:-$HOME/AI项目外部环境/考勤管理系统/venv}"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "📦 首次运行，正在创建外部虚拟环境..."
    mkdir -p "$(dirname "$VENV_DIR")"
    python3 -m venv "$VENV_DIR" || exit 1
    "$VENV_DIR/bin/python" -m pip install -r requirements.txt || exit 1
fi

echo "🕐 考勤管理系统启动中..."
export PYTHONDONTWRITEBYTECODE=1
exec "$VENV_DIR/bin/python" app.py
