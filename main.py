"""Main FastAPI application"""
import os
import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from routes import router as api_router
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from rich.logging import RichHandler

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "class": "rich.logging.RichHandler",
            "formatter": "default",
            "level": "DEBUG",
            "rich_tracebacks": True,
            "show_time": True,
            "show_path": False,
            "log_time_format": "%Y-%m-%d %H:%M:%S",
            "markup": True
        },
    },
    "loggers": {
        "uvicorn": {
             "handlers": ["default"],
             "level": "INFO",
             "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["default"],
            "level": "INFO", 
            "propagate": False,
        },
        "": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "finance_db")
MAX_UPLOAD_SIZE = 1 * 1024 * 1024
UPLOAD_ENDPOINT_PATH = "/api/upload"
SAVE_AT_FRONT = os.getenv("SAVE_AT_FRONT", "false").lower() == "true"

if not MONGODB_URI:
    logger.error("MONGODB_URI environment variable not set! Database connection will fail.")

app_state = {}

limiter = Limiter(key_func=get_remote_address)
DEFAULT_RATE_LIMIT = "15/minute"

class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == UPLOAD_ENDPOINT_PATH:
            content_length_header = request.headers.get("content-length")
            if content_length_header:
                try:
                    content_length = int(content_length_header)
                    if content_length > MAX_UPLOAD_SIZE:
                        logger.warning(f"Upload rejected: File size {content_length} exceeds limit {MAX_UPLOAD_SIZE}.")
                        return Response(f"Maximum file upload size limit ({MAX_UPLOAD_SIZE / (1024*1024):.1f} MB) exceeded.", status_code=413)
                except ValueError:
                    logger.warning("Upload rejected: Invalid Content-Length header.")
                    return Response("Invalid Content-Length header.", status_code=400)

        response = await call_next(request)
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Connecting to MongoDB at {MONGODB_URI}...")
    try:
        app_state["db_client"] = AsyncIOMotorClient(MONGODB_URI)
        app_state["db"] = app_state["db_client"][DB_NAME]
        app_state["expenses_collection"] = app_state["db"].get_collection("expenses")
        logger.info(f"Successfully connected to MongoDB database: {DB_NAME}")
        app_state["save_at_front"] = SAVE_AT_FRONT
        logger.info(f"Configuration: SAVE_AT_FRONT = {SAVE_AT_FRONT}")
        await app_state["db_client"].admin.command('ping')
        logger.info("MongoDB ping successful.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        app_state["db_client"] = None
        app_state["db"] = None
        app_state["expenses_collection"] = None
    
    yield
    
    if app_state.get("db_client"):
        logger.info("Closing MongoDB connection...")
        app_state["db_client"].close()
        logger.info("MongoDB connection closed.")

app = FastAPI(
    title="Finance Manager API",
    description="API for managing expenses from files and text.",
    version="0.1.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LimitUploadSizeMiddleware)

app.include_router(
    api_router, 
    prefix="/api", 
    tags=["api"],
)

app.mount("/", StaticFiles(directory="public", html=True), name="static")

@app.middleware("http")
async def add_app_config_to_request(request: Request, call_next):
    """Adds database connection and configuration settings to the request state."""
    request.state.db_client = app_state.get("db_client")
    request.state.db = app_state.get("db")
    request.state.expenses_collection = app_state.get("expenses_collection")
    request.state.save_at_front = app_state.get("save_at_front", False)
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    ) 