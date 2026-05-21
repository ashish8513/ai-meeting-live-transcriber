from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.database import init_db
from api.routers import admin, auth, internal

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db()
        print(f"Auth DB ready: {settings.database_url.split('://')[0]}")
    except Exception as exc:
        print(f"Auth DB init warning: {exc}")
    yield


app = FastAPI(
    title="MeetScribe Auth API",
    version="1.0.0",
    description="JWT auth, PostgreSQL storage, admin dashboard data",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(internal.router, prefix="/api")


@app.get("/health")
def health():
    db_ok = True
    try:
        from sqlalchemy import text

        from api.database import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok", "service": "auth-api", "database": db_ok}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=int(__import__("os").getenv("AUTH_API_PORT", "8200")), reload=False)
