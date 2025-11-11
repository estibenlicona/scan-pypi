"""
HTTP Interface - FastAPI application for HTTP endpoints.

Follows Clean Architecture: only handles HTTP concerns,
delegates business logic to application layer.
"""

from __future__ import annotations
from contextlib import asynccontextmanager
from typing import List, Dict, Any
from fastapi import FastAPI, Body, HTTPException
from src.application.dtos import AnalysisRequest
from src.application.bootstrap import ApplicationFactory

# Application components - initialized during lifespan startup
_orchestrator = None
_container = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events.
    
    Follows Single Responsibility: only HTTP lifecycle management.
    Initializes application components at the right time.
    """
    global _orchestrator, _container
    
    try:
        # Startup - initialize application components at the right time
        _orchestrator, _container = ApplicationFactory.create_application()
        _container.logger.info("PyPI Package Scanner API starting up")
        
        yield  # Application runs here
        
    finally:
        # Shutdown - cleanup resources
        if _container:
            _container.logger.info("PyPI Package Scanner API shutting down")
            if hasattr(_container, 'close'):
                _container.close()


# Create FastAPI app with clean configuration
app = FastAPI(
    title="PyPI Package Scanner",
    description="Analyze Python packages for vulnerabilities and compliance",
    version="2.0.0",
    lifespan=lifespan
)


@app.post("/scan/")
async def scan_requirements(
    libraries: List[str] = Body(..., embed=True)
) -> Dict[str, Any]:
    """
    Analyze Python packages for vulnerabilities and compliance.
    
    Follows Clean Architecture: delegates to application layer,
    only handles HTTP-specific concerns (validation, serialization).
    
    Args:
        libraries: List of package names to analyze
        
    Returns:
        Analysis report with packages, vulnerabilities, and metadata
        
    Raises:
        HTTPException: If validation fails or analysis errors occur
    """
    # Input validation (HTTP layer responsibility)
    if not libraries:
        raise HTTPException(
            status_code=400, 
            detail="Libraries list cannot be empty"
        )

    if _orchestrator is None or _container is None:
        raise RuntimeError("Application not initialized")
    
    # Log HTTP request (observability)
    _container.logger.info(
        f"HTTP scan requested for {len(libraries)} packages: {libraries}"
    )
    
    try:
        
        # Create domain request object
        request = AnalysisRequest(libraries=libraries)
        
        # Delegate to application layer (business logic)
        report = await _orchestrator.run(request)
        
        # Log success
        _container.logger.info("HTTP scan completed successfully")
        
        # Transform to HTTP response format (presentation layer responsibility)
        response_data: Dict[str, Any] = {
            "timestamp": report.timestamp,
            "vulnerabilities": report.vulnerabilities,
            "packages": report.packages,
            "filtered_packages": report.filtered_packages,
            "summary": report.summary
        }
        
        return response_data
        
    except ValueError as e:
        # Business validation errors
        _container.logger.warning(f"Invalid analysis request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Unexpected system errors
        _container.logger.error(f"Analysis pipeline failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal analysis error occurred"
        )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns basic service status for monitoring/load balancers.
    """
    return {
        "status": "healthy", 
        "version": "2.0.0",
        "service": "pypi-package-scanner"
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint with API information.
    
    Provides service discovery information for clients.
    """
    return {
        "service": "PyPI Package Scanner API",
        "version": "2.0.0",
        "documentation": "/docs",
        "health_check": "/health",
        "scan_endpoint": "/scan/"
    }