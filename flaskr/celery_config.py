from celery import Celery
from flask import Flask, current_app
import logging

logger = logging.getLogger('flaskr.celery_config')

def make_celery(app: Flask = None):
    logger.info("Initializing Celery...")
    try:
        celery = Celery(
            'flaskr',
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
            worker_redirect_stdouts_level='INFO'
        )
        
        if app:
            config = {
                'broker_url': app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
                'result_backend': app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
            }
            celery.conf.update(config)
            
            class ContextTask(celery.Task):
                abstract = True
                
                def __call__(self, *args, **kwargs):
                    if not current_app:
                        with app.app_context():
                            return self.run(*args, **kwargs)
                    return self.run(*args, **kwargs)
                    
            celery.Task = ContextTask
            
        return celery
        
    except Exception as e:
        logger.error(f"Error initializing Celery: {str(e)}")
        raise

celery = make_celery()

def init_app(app):
    global celery
    celery = make_celery(app)
    return celery