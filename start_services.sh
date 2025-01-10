#!/bin/bash

# 启动 Redis（如果需要）
# redis-server &

# 启动 Celery worker
celery -A celery_worker.celery worker --loglevel=INFO &

# 启动 Flask 应用
flask --app flaskr run --host=0.0.0.0 --port=5000