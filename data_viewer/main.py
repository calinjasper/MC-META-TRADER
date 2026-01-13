"""
Trading Data Viewer - FastAPI Application
Main entry point for the web platform
Supports MySQL (ticks, minute) and PocketBase (trades, signals) data sources
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader
import logging

from data_viewer.config import STATIC_DIR, TEMPLATES_DIR, HOST, PORT, DEBUG
from data_viewer.api import collections, data, download, backtest

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Trading Data Viewer",
    description="Web platform for downloading and visualizing trading data from MySQL and PocketBase",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")

# Setup templates
try:
    template_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
except Exception as e:
    logger.error(f"Failed to setup templates: {e}")
    template_env = None

# Include API routers
app.include_router(collections.router)
app.include_router(data.router)
app.include_router(download.router)
app.include_router(backtest.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page"""
    if template_env:
        template = template_env.get_template("index.html")
        return HTMLResponse(template.render(request=request))
    else:
        return HTMLResponse("<h1>Error: Templates not available</h1>")


@app.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    """Backtester page"""
    if template_env:
        template = template_env.get_template("backtest.html")
        return HTMLResponse(template.render(request=request))
    else:
        return HTMLResponse("<h1>Error: Templates not available</h1>")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "data_viewer.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG
    )

