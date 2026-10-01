import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from app.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

try:
    pg_pool = pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
except Exception as e:
    print(f"[ERROR] Failed to initialize Postgres connection pool: {e}")
    pg_pool = None


@contextmanager
def get_db():
    if pg_pool is None:
        raise RuntimeError("Database connection pool is not initialized.")
    conn = pg_pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pg_pool.putconn(conn)
