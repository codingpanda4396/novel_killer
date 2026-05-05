#!/bin/bash
# 加载 .env 文件中的环境变量
# 使用方法：source scripts/load_env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
    echo "DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:+SET}"
    echo "RIGHTCODE_API_KEY: ${RIGHTCODE_API_KEY:+SET}"
else
    echo "Warning: .env file not found. Please copy .env.example to .env and fill in your API keys."
fi

# 激活虚拟环境（如果存在）
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi
