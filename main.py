"""Main FastAPI application"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
# Import routers later
from routes import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file in the backend directory
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "finance_db") # Default DB name if not set

if not MONGODB_URI:
    logger.error("MONGODB_URI environment variable not set! Database connection will fail.")
    # Optionally raise an error:
    # raise EnvironmentError("MONGODB_URI is not set in the environment variables.")

# Application state to hold the database client and collection
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    logger.info(f"Connecting to MongoDB at {MONGODB_URI}...")
    try:
        app_state["db_client"] = AsyncIOMotorClient(MONGODB_URI)
        app_state["db"] = app_state["db_client"][DB_NAME]
        app_state["expenses_collection"] = app_state["db"].get_collection("expenses")
        logger.info(f"Successfully connected to MongoDB database: {DB_NAME}")
        await app_state["db_client"].admin.command('ping')
        logger.info("MongoDB ping successful.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        app_state["db_client"] = None
        app_state["db"] = None
        app_state["expenses_collection"] = None
    
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

# Add CORS middleware (still useful if API is called from other origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
app.include_router(api_router, prefix="/api")

# Mount static files directory (MUST be after API router)
app.mount("/", StaticFiles(directory="public", html=True), name="static")

# Make app state accessible via middleware
@app.middleware("http")
async def add_db_to_request(request, call_next):
    request.state.db_client = app_state.get("db_client")
    request.state.db = app_state.get("db")
    request.state.expenses_collection = app_state.get("expenses_collection")
    response = await call_next(request)
    return response

# Removed old root endpoint - StaticFiles serves index.html at "/"
# @app.get("/")
# async def read_root():
#     return {"message": "Welcome to the Finance Manager API"}

# Removed startup/shutdown event handlers as lifespan is preferred

if __name__ == "__main__":
    import uvicorn
    # Now run from the root directory
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 