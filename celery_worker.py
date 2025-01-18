#!/usr/bin/env python3
from flaskr import create_app
from flaskr.celery_config import celery
from flaskr.tasks import (
    process_pca,
    process_admixture,
    process_f3,
    process_f4,
    process_qpwave  # 确保导入 qpwave 任务
)

# 创建 Flask 应用实例
flask_app = create_app()

# 确保在应用上下文中运行
flask_app.app_context().push()

# 不需要显式更新配置，因为在 create_app 中已经完成了配置 
# 确保 celery 对象被使用

# 这样可以确保所有任务都被正确注册
__all__ = [
    'celery',
    'process_pca',
    'process_admixture',
    'process_f3',
    'process_f4',
    'process_qpwave'
]