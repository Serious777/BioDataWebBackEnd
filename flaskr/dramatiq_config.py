import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend
import logging
from flask import Flask

logger = logging.getLogger('flaskr.dramatiq_config')

# 创建 Redis backend 和 broker
result_backend = RedisBackend(url="redis://localhost:6379/1")
redis_broker = RedisBroker(url="redis://localhost:6379/0")

# 添加结果中间件
redis_broker.add_middleware(Results(backend=result_backend))

# 设置 broker
dramatiq.set_broker(redis_broker)

def init_app(app: Flask):
    """初始化 Dramatiq"""
    logger.info("Initializing Dramatiq...")
    try:
        # 启动 worker 进程
        import multiprocessing
        worker_process = multiprocessing.Process(
            target=lambda: dramatiq.cli.main(['dramatiq', 'flaskr.tasks', '--processes', '1'])
        )
        worker_process.daemon = True
        worker_process.start()
        logger.info(f"Dramatiq worker process started with PID: {worker_process.pid}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Dramatiq: {str(e)}")
        raise 