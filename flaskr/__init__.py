import os
import logging
from flask import Flask
from flask_cors import CORS


def create_app(test_config=None):
    # create and configure the app
    # 允许指定的域名进行跨域请求
    allowed_origins = [
        "http://localhost:3000",  # 开发环境
        # 生产环境

    ]
    app = Flask(__name__, instance_relative_config=True, template_folder='templates')
    app.config['DEBUG'] = True

    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )
    # 设置日志级别和格式
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    return app
