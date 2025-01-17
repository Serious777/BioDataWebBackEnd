#!/bin/bash

# 设置环境变量
export PYTHONPATH=/root/project-dev/backend


# 启动 Celery worker
# 使用单个 worker，限制并发数
python -m celery -A celery_worker.celery worker \
    -l INFO \
    --pool=solo \
    --concurrency=1 \
    --max-tasks-per-child=1