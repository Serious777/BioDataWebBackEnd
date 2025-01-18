#!/bin/bash

# 确保脚本退出时清理所有子进程
cleanup() {
    echo "正在清理进程..."
    # 终止 Celery worker 进程
    pkill -f 'celery.*worker'
    # 等待进程完全终止
    sleep 2
    exit 0
}

# 注册清理函数
trap cleanup SIGINT SIGTERM

# 激活 conda 环境
conda activate my_env

# 确保没有遗留的 Celery 进程
pkill -f 'celery.*worker'
sleep 2

# 启动 Celery worker
source start_celery.sh &

# 等待确保 Celery 启动
sleep 2

# 启动 Flask 应用
flask --app flaskr run --host=0.0.0.0 --port=5000