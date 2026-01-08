from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

from remarkable import config

_customer = "guosen"

remote_url = URL(
    drivername="mysql+pymysql",
    host=config.get_config(f"{_customer}.db.host"),
    port=config.get_config(f"{_customer}.db.port"),
    username=config.get_config(f"{_customer}.db.user"),
    password=config.get_config(f"{_customer}.db.password"),
    database=config.get_config(f"{_customer}.db.dbname"),
    query={"charset": "utf8"},
)

engine = create_engine(
    remote_url, pool_pre_ping=True, pool_recycle=3600
)  # 需要配置pool_recycle, mysql会主动关闭超时连接


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = sessionmaker(engine)()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
