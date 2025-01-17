from celery import Celery
from flask import Flask
import logging

logger = logging.getLogger('flaskr.celery_config')

def make_celery(app: Flask = None):
    logger.info("Initializing Celery...")
    try:
        celery = Celery(
            'flaskr',
            include=['flaskr.tasks'],
            broker='redis://localhost:6379/0',
            result_backend='redis://localhost:6379/1'
        )
        
        celery.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='Asia/Shanghai',
            enable_utc=True,
            task_track_started=True,
            worker_redirect_stdouts=True,
            worker_redirect_stdouts_level='INFO',
            broker_connection_retry_on_startup = True

        )
        
        if app:
            celery.conf.update(
                broker_url=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
                result_backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
                task_track_started=app.config.get('CELERY_TASK_TRACK_STARTED', True),
                task_time_limit=app.config.get('CELERY_TASK_TIME_LIMIT', 36000)
            )
            
            class ContextTask(celery.Task):
                abstract = True
                def __call__(self, *args, **kwargs):
                    with app.app_context():
                        return self.run(*args, **kwargs)
                    
            celery.Task = ContextTask
            
        return celery
        
    except Exception as e:
        logger.error(f"Error initializing Celery: {str(e)}")
        raise

celery = make_celery()

def init_app(app):
    """初始化 Celery 与 Flask 应用的集成"""
    global celery
    celery = make_celery(app)
    return celery