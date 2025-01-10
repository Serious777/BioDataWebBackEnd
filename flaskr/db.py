from flask import current_app, g
import mysql
from mysql.connector import Error

def get_db():
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(
                host=current_app.config['MYSQL_HOST'],
                user=current_app.config['MYSQL_USER'],
                password=current_app.config['MYSQL_PASSWORD'],
                database=current_app.config['MYSQL_DB']
            )
        except Error as e:
            current_app.logger.error(f"Error connecting to MySQL Platform: {e}")
            raise
    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        try:
            db.close()
        except Error as e:
            current_app.logger.error(f"Error closing MySQL connection: {e}")

def init_app(app):
    # 添加 MySQL 数据库配置
    app.config.from_mapping(
        MYSQL_HOST='127.0.0.1',  # 你的 MySQL 服务器地址
        MYSQL_USER='root',  # 你的 MySQL 用户名
        MYSQL_PASSWORD='142536',  # 你的 MySQL 密码
        MYSQL_DB='biodatabase'  # 你的数据库名称
    )
    # 注册关闭数据库连接的函数
    app.teardown_appcontext(close_db)
    # 添加 CLI 命令

    #app.cli.add_command(init_db_command)