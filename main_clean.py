from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from datetime import datetime
import logging

from app.core.database import engine
from app.api.blog_routes import router as blog_router
from app.api.webhook_routes import router as webhook_router
from models import Base

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Blog Application", version="1.0.0")

@app.on_event("startup")
async def startup():
    try:
        logger.info("Starting application...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.get("/")
async def root():
    return RedirectResponse(url="/blog")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Include routers
app.include_router(blog_router, prefix="/blog", tags=["blogs"])
app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)