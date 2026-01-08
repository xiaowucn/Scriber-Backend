from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import class_mapper, scoped_session, sessionmaker

from remarkable.config import get_config


class Base:
    def to_dict(self):
        mapper = class_mapper(self.__class__)
        column_names = [column.key for column in mapper.columns]
        return {column: getattr(self, column) for column in column_names}


class Database:
    def __init__(self, config: dict):
        self.config = config
        self.engine = self.create_engine()
        self.session = scoped_session(sessionmaker(bind=self.engine))

    def get_dsn_str(self):
        db_config = self.config
        user = db_config["user"]
        password = db_config["password"]
        dsn = db_config["dsn"]
        return f"oracle+cx_oracle://{user}:{password}@{dsn}"

    def create_engine(self):
        dns = self.get_dsn_str()
        return create_engine(
            dns, optimize_limits=True, echo=True, pool_size=10, max_overflow=5, pool_recycle=3600, pool_pre_ping=True
        )

    def connect(self):
        return self.session()

    @contextmanager
    def session_scope(self):
        session = self.connect()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


db = Database(get_config("customer_settings.oracle"))
BaseModel = declarative_base(cls=Base)
