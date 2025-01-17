#!/bin/bash

# 启动 Redis（如果需要）
# redis-server &
conda activate my_env

# 启动 Celery worker（在后台运行）
source start_celery.sh &

# 等待几秒确保 Celery 启动
sleep 2

# 启动 Flask 应用
flask --app flaskr run --host=0.0.0.0 --port=5000