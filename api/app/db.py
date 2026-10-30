from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

engine = create_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1),
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(attempts: int = 30, delay: float = 2.0):
    import json
    import logging
    import time

    from sqlalchemy import text

    log = logging.getLogger("sop.db")
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            if attempt > 1:
                log.info(json.dumps({"event": "db_ready", "attempt": attempt}))
            return
        except Exception as e:
            log.warning(json.dumps({"event": "db_wait", "attempt": attempt, "error": type(e).__name__}))
            time.sleep(delay)
    raise RuntimeError("Database not reachable after waiting")
