#!/bin/bash

# 设置环境变量
export PYTHONPATH=/root/my-project/web-database-backend/backend

# 启动 Celery worker
celery -A celery_worker.celery worker --loglevel=INFO
