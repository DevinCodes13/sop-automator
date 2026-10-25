import os
import psycopg
from fastapi import FastAPI

app = FastAPI(title="SOP Automator API")
DATABASE_URL = os.environ["DATABASE_URL"]

@app.get("/api/health")
def health():
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        db = "ok"
    except Exception:
        db = "down"
    return {"api": "ok", "db": db}
