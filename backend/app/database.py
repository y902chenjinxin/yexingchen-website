from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# SQLite不使用连接池
is_sqlite = "sqlite" in settings.DATABASE_URL
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {
    "connect_args": connect_args,
}
# 非SQLite数据库启用连接池
if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()