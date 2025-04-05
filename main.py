"""Main FastAPI application"""
import os
import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
# Import routers later
from routes import router as api_router
# Removed logging.config import
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response # Import Response

# Import RichHandler for colored logging
from rich.logging import RichHandler

# --- Add slowapi imports ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware # Import the middleware

# --- Unified Logging Configuration with Rich ---
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            # RichHandler will handle timestamp and color, format is less critical here
            # but we can define basic structure if needed by other handlers potentially.
            "format": "%(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S", # RichHandler uses its own time format by default
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
        "": { # Root logger for our application
            "handlers": ["default"],
            "level": "INFO", # Set desired level for app logs (INFO or DEBUG)
            "propagate": False,
        },
    },
}

# Apply logging configuration directly
logging.config.dictConfig(LOGGING_CONFIG)

# Get application logger instance (will use the config above)
logger = logging.getLogger(__name__)

# Load environment variables from .env file in the backend directory
# Ensure this path is correct if main.py is at the root
# dotenv_path = os.path.join(os.path.dirname(__file__), '.env') 
load_dotenv() # Simpler: load_dotenv searches current dir and parents

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "finance_db") # Default DB name if not set
MAX_UPLOAD_SIZE = 1 * 1024 * 1024  # 1MB limit
UPLOAD_ENDPOINT_PATH = "/api/upload" # Define the upload path constant
SAVE_AT_FRONT = os.getenv("SAVE_AT_FRONT", "false").lower() == "true" # Read SAVE_AT_FRONT

if not MONGODB_URI:
    logger.error("MONGODB_URI environment variable not set! Database connection will fail.")
    # Optionally raise an error:
    # raise EnvironmentError("MONGODB_URI is not set in the environment variables.")

# Application state to hold the database client and collection
app_state = {}

# --- Rate Limiter Setup ---
# Removed storage_uri to default to in-memory storage
limiter = Limiter(key_func=get_remote_address)
DEFAULT_RATE_LIMIT = "15/minute" # Define the rate limit string

# --- Middleware for Upload Size Limit ---
class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if the request path matches the upload endpoint
        if request.url.path == UPLOAD_ENDPOINT_PATH:
            content_length_header = request.headers.get("content-length")
            if content_length_header:
                try:
                    content_length = int(content_length_header)
                    if content_length > MAX_UPLOAD_SIZE:
                        logger.warning(f"Upload rejected: File size {content_length} exceeds limit {MAX_UPLOAD_SIZE}.")
                        # Use Starlette Response for custom body
                        return Response(f"Maximum file upload size limit ({MAX_UPLOAD_SIZE / (1024*1024):.1f} MB) exceeded.", status_code=413)
                except ValueError:
                    logger.warning("Upload rejected: Invalid Content-Length header.")
                    return Response("Invalid Content-Length header.", status_code=400)
            # Note: If Content-Length is missing (e.g., chunked encoding), FastAPI handles streaming,
            # but this middleware won't catch the size limit upfront.
            # More complex streaming checks could be added if needed.

        response = await call_next(request)
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    logger.info(f"Connecting to MongoDB at {MONGODB_URI}...")
    try:
        app_state["db_client"] = AsyncIOMotorClient(MONGODB_URI)
        app_state["db"] = app_state["db_client"][DB_NAME]
        app_state["expenses_collection"] = app_state["db"].get_collection("expenses")
        logger.info(f"Successfully connected to MongoDB database: {DB_NAME}")
        # Store SAVE_AT_FRONT in app state
        app_state["save_at_front"] = SAVE_AT_FRONT
        logger.info(f"Configuration: SAVE_AT_FRONT = {SAVE_AT_FRONT}")
        await app_state["db_client"].admin.command('ping')
        logger.info("MongoDB ping successful.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        app_state["db_client"] = None
        app_state["db"] = None
        app_state["expenses_collection"] = None
    
    # --- Moved Rate Limiter Setup outside lifespan ---
    # app.state.limiter = limiter
    # app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    # app.add_middleware(SlowAPIMiddleware)
    
    yield # Application runs here
    
    # Shutdown: Close MongoDB connection
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

# --- Apply Rate Limiter State and Handler (Moved Here) ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Add Middleware (Moved Here - Order Matters) ---
# 1. Rate Limiter Middleware (TEMPORARILY DISABLED)
# app.add_middleware(SlowAPIMiddleware)
# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 3. Upload Size Limit Middleware (Re-enabled)
app.add_middleware(LimitUploadSizeMiddleware)

# --- API Routes (Apply rate limiting via dependency - TEMPORARILY DISABLED) ---
app.include_router(
    api_router, 
    prefix="/api", 
    tags=["api"],
    # Apply the rate limiter as a dependency to all routes in this router
    # dependencies=[Depends(limiter.limit(DEFAULT_RATE_LIMIT))]
)

# Mount static files directory (MUST be after API router)
app.mount("/", StaticFiles(directory="public", html=True), name="static")

# Make app state accessible via middleware
@app.middleware("http")
async def add_app_config_to_request(request: Request, call_next):
    """Adds database connection and configuration settings to the request state."""
    request.state.db_client = app_state.get("db_client")
    request.state.db = app_state.get("db")
    request.state.expenses_collection = app_state.get("expenses_collection")
    request.state.save_at_front = app_state.get("save_at_front", False) # Add save_at_front
    response = await call_next(request)
    return response

# Removed old root endpoint - StaticFiles serves index.html at "/"
# @app.get("/")

# Removed startup/shutdown event handlers as lifespan is preferred

if __name__ == "__main__":
    import uvicorn
    # Now run from the root directory
    # Uvicorn will use its default logging for its own messages (with colors)
    # Our application logs will use the RichHandler configured above
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    ) 