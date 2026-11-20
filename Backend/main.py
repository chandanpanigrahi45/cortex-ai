from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, Base, get_db
from routers import user, credits, agents, payments
from cache import get_redis
import models

app = FastAPI(title="Cortex AI Multi-Agent API")

# CORS - allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database tables create karna
try:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"
        ))
    print("[OK] Database tables initialized successfully")
except Exception as e:
    print(f"[WARNING] Could not initialize database tables: {e}")

# Register Routers
app.include_router(user.router)
app.include_router(credits.router)
app.include_router(agents.router)
app.include_router(payments.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Cortex AI Master API!"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Healthy", "postgres_connected": True}
    except Exception as e:
        return {"status": "System Fault", "error": str(e)}
