from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uvicorn
from .utils.config import settings
from .utils.database import engine, Base
from .routers import auth, instances, templates, billing
from .services.azure_manager import AzureGPUManager
from .services.autopause import AutoPauseEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global services
azure_manager = None
autopause_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global azure_manager, autopause_engine
    
    # Startup
    logger.info("Starting GPU Cloud Platform...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize services
    azure_manager = AzureGPUManager()
    autopause_engine = AutoPauseEngine(azure_manager)
    
    # Start AutoPause engine
    await autopause_engine.start()
    
    logger.info("GPU Cloud Platform started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GPU Cloud Platform...")
    await autopause_engine.stop()
    logger.info("Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="GPU Cloud Platform",
    description="Deploy GPUs in 10 seconds, save 70% with AutoPause",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(instances.router, prefix="/api/instances", tags=["Instances"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "GPU Cloud Platform",
        "version": "1.0.0",
        "status": "operational",
        "message": "Deploy GPUs in 10 seconds, save 70% with AutoPause"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "database": "connected",
            "azure": "connected" if azure_manager else "disconnected",
            "autopause": "running" if autopause_engine and autopause_engine.is_running else "stopped"
        }
    }

@app.get("/api/stats")
async def platform_stats():
    """Get platform statistics"""
    if not autopause_engine:
        raise HTTPException(status_code=503, detail="AutoPause engine not initialized")
    
    analytics = autopause_engine.get_analytics()
    
    return {
        "total_instances": analytics["total_instances_monitored"],
        "currently_paused": analytics["currently_paused"],
        "total_savings": f"${analytics['total_savings_all_time']:.2f}",
        "total_pause_hours": f"{analytics['total_pause_hours']:.1f}",
        "pause_efficiency": f"{analytics['pause_efficiency']:.1f}%"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )