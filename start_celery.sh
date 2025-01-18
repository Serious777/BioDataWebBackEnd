#!/bin/bash

# 设置环境变量
export PYTHONPATH=/root/project-dev/backend

# 确保使用唯一的 worker 名称（使用时间戳）
TIMESTAMP=$(date +%s)
WORKER_NAME="worker_${TIMESTAMP}@VM-16-15-debian"

# 启动 Celery worker
celery -A celery_worker.celery worker \
    --loglevel=INFO \
    -n "$WORKER_NAME" \
    --pidfile="/tmp/celery_${TIMESTAMP}.pid"

