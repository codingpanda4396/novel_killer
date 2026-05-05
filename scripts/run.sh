#!/bin/bash
# NovelOps 运行脚本 - 自动加载环境变量
# 使用方法：./scripts/run.sh python3 -m novelops.cli ask "查看状态"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

# 加载 .env 文件
if [ -f ".env" ]; then
    echo "Loading .env..."
    set -a
    source .env
    set +a
else
    echo "Warning: .env file not found. Please copy .env.example to .env"
fi

# 激活虚拟环境（如果存在）
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# 执行命令
exec "$@"
