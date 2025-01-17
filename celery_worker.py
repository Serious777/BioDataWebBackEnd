#!/usr/bin/env python3
from flaskr import create_app
from flaskr.celery_config import celery

# 创建 Flask 应用实例
flask_app = create_app()

# 确保在应用上下文中运行
flask_app.app_context().push()

# 不需要显式更新配置，因为在 create_app 中已经完成了配置 
# 确保 celery 对象被使用
if __name__ == '__main__':
    celery.start()