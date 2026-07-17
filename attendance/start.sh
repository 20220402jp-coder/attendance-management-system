#!/usr/bin/env bash
# 考勤系统启动脚本
cd "$(dirname "$0")"

VENV_DIR="/Users/phoenix/AI项目外部环境/考勤管理系统/venv"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "❌ 找不到外部虚拟环境: $VENV_DIR"
    echo "请先重新创建虚拟环境并安装 requirements.txt"
    exit 1
fi

echo "🕐 考勤管理系统启动中..."
export PYTHONDONTWRITEBYTECODE=1
exec "$VENV_DIR/bin/python" app.py
