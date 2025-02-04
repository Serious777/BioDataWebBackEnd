from flask import current_app, g
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool

# 创建基类
Base = declarative_base()

def get_db():
    if 'db' not in g:
        try:
            # 创建数据库引擎，设置连接池参数
            engine = create_engine(
                f'mysql+mysqlconnector://{current_app.config["MYSQL_USER"]}:'
                f'{current_app.config["MYSQL_PASSWORD"]}@{current_app.config["MYSQL_HOST"]}/'
                f'{current_app.config["MYSQL_DB"]}',
                poolclass=QueuePool,
                pool_size=10,  # 连接池大小
                max_overflow=20,  # 超过pool_size后最多可以创建的连接数
                pool_timeout=30,  # 连接池中没有可用连接的等待时间
                pool_recycle=1800,  # 连接在连接池中重复使用的时间间隔（秒）
                pool_pre_ping=True  # 每次从连接池获取连接时ping一下服务器，确保连接有效
            )
            
            # 创建session工厂
            session_factory = sessionmaker(bind=engine)
            
            # 创建线程安全的scoped session
            g.db = scoped_session(session_factory)
            
            # 将Base绑定到engine
            Base.metadata.bind = engine
            
        except Exception as e:
            current_app.logger.error(f"Error connecting to MySQL Platform: {e}")
            raise
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.remove()  # 移除当前线程的session
        except Exception as e:
            current_app.logger.error(f"Error closing SQLAlchemy session: {e}")

def init_app(app):
    # 添加 MySQL 数据库配置
    app.config.from_mapping(
        MYSQL_HOST='127.0.0.1',
        MYSQL_USER='root',
        MYSQL_PASSWORD='142536',
        MYSQL_DB='biodatabase',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,  # 关闭追踪修改
        SQLALCHEMY_ECHO=False  # 是否显示SQL语句
    )
    
    # 注册关闭数据库连接的函数
    app.teardown_appcontext(close_db)

    #app.cli.add_command(init_db_command)