#!/usr/bin/env python3
import os
from flaskr import create_app
from flaskr.celery_config import celery

# 创建 Flask 应用实例
flask_app = create_app()
flask_app.app_context().push()

# 更新 Celery 配置
celery.conf.update(flask_app.config) 