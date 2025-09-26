import asyncio
import sys
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import fastapi
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Application constants
SERVER_HOST = os.getenv("HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "8005"))

# Directory constants
THIS_DIR = Path(__file__).parent
STATIC_DIR = THIS_DIR / "static"
TEMPLATES_DIR = THIS_DIR / "templates"

# Windows-specific asyncio configuration
if sys.platform == "win32":
    try:
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        print("✅ Windows ProactorEventLoop policy set")
    except Exception as e:
        print(f"⚠️  Warning: Could not set Windows event loop policy: {e}")

# Set ANYIO backend for better async compatibility
os.environ.setdefault('ANYIO_BACKEND', 'asyncio')

# Detect environment (development or production)
ENV = os.environ.get("ENV", "production").lower()
RELOAD = ENV == "development" and sys.platform != "win32"
WORKERS = 1 if sys.platform == "win32" else (2 if ENV == "development" else 1)
LOG_LEVEL = logging.DEBUG if ENV == "development" else logging.INFO

# Configure comprehensive logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Logging level set to {logging.getLevelName(LOG_LEVEL)} (ENV={ENV})")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    logger.info("🚀 Starting application lifespan")
    try:
        logger.info("✅ Application startup complete - Ready to serve!")
        yield
    except Exception as e:
        logger.error(f"❌ Critical error during application startup: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize application: {str(e)}")
    finally:
        logger.info("🔄 Application shutdown initiated")

# Create FastAPI app with enhanced configuration
app = FastAPI(
    title="AI Personal Assistant API",
    description="Robust AI Personal Assistant with multi-agent orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount static files with existence check
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    logger.info(f"✅ Static files mounted from {STATIC_DIR}")

# Root endpoint
@app.get("/")
async def index(request: Request):
    template_path = TEMPLATES_DIR / "index.html"
    if template_path.exists():
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return {
            "message": "AI Personal Assistant API",
            "status": "Template not found - API endpoints available",
            "template_path": str(template_path),
            "endpoints": ["/chat/", "/health", "/status"]
        }

# Exception handlers
@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception) -> fastapi.responses.JSONResponse:
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return fastapi.responses.JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "timestamp": "timestamp",
            "path": str(request.url.path)
        }
    )

if __name__ == "__main__":
    import uvicorn

    # Create required directories
    for directory in ["static", "templates"]:
        dir_path = THIS_DIR / directory
        dir_path.mkdir(exist_ok=True)
        logger.info(f"📁 Ensured directory exists: {dir_path}")

    logger.info("🚀 Starting AI Personal Assistant Server...")
    logger.info(f"🖥️  Platform: {sys.platform}")
    logger.info(f"🐍 Python: {sys.version.split()[0]}")
    logger.info("🔗 Single Port Operation: All services on port 8005")

    try:
        uvicorn.run(
            "__main__:app",
            host="0.0.0.0",
            port=8005,
            log_level="info",
            reload=RELOAD,
            workers=WORKERS,
            access_log=True,
            use_colors=True
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}", exc_info=True)
        sys.exit(1)
