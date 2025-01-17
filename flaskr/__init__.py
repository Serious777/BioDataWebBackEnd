import os
import logging
from flask import Flask
from flask_cors import CORS
from . import celery_config  # 使用相对导入

def create_app(test_config=None):
    # create and configure the app
    # 允许指定的域名进行跨域请求
    allowed_origins = [
        "http://localhost:3000",  # 开发环境
        # 生产环境

    ]
    # 设置日志级别和格式
    # 在创建 Flask app 之前配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True  # 强制重新配置日志
    )
    
    # 创建 logger
    logger = logging.getLogger('flaskr')
    # 确保日志信息输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    app = Flask(__name__, instance_relative_config=True, template_folder='templates')
    app.config['DEBUG'] = True
   # 配置 Flask 的日志处理
    app.logger.handlers = []  # 清除默认处理程序
    app.logger.addHandler(console_handler)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    # init database
    from . import db
    db.init_app(app)

    # from . import auth
    # app.register_blueprint(auth.bp)
    from . import biodata
    app.register_blueprint(biodata.bp)
    from . import tools
    app.register_blueprint(tools.bp)

    # 配置 Celery
    app.config.update(
        CELERY_BROKER_URL='redis://localhost:6379/0',
        CELERY_RESULT_BACKEND='redis://localhost:6379/1',
        CELERY_TASK_TRACK_STARTED=True,
        CELERY_TASK_TIME_LIMIT=36000
    )
    
    # 初始化 Celery
    try:
        logging.info("Celery initialized successfully with app context")
    except Exception as e:
        logging.error(f"Failed to initialize Celery: {str(e)}")

    return app