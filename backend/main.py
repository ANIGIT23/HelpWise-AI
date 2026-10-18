from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Initialize FastAPI application
# FastAPI automatically creates interactive OpenAPI documentation at /docs and /redoc
app = FastAPI(
    title="HelpWise AI — ITSM Helpdesk Backend",
    description="Core REST API service for HelpWise AI ITSM Helpdesk application",
    version="1.0.0",
)

# CORS (Cross-Origin Resource Sharing) Middleware Configuration
# Why CORS is needed:
# The React frontend typically runs on port 5173 (http://localhost:5173),
# while this FastAPI backend runs on port 8000 (http://127.0.0.1:8000).
# Browsers enforce the 'Same-Origin Policy' for security. By configuring CORS,
# we permit the frontend origin to make HTTP requests to this backend.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all standard and custom headers
)


# Pydantic schema for response validation and automatic API docs
class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    timestamp: str
    environment: str


@app.get(
    "/",
    tags=["Root"],
    summary="Root Welcome Endpoint",
    description="Returns welcome message and links to API documentation."
)
def root_endpoint() -> Dict[str, Any]:
    """Root endpoint to verify that the service is responsive."""
    return {
        "message": "Welcome to HelpWise AI — ITSM Helpdesk Backend API",
        "docs_url": "/docs",
        "health_check": "/health",
        "status": "operational"
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Monitoring"],
    summary="Health Check Endpoint",
    description="Returns operational status of the backend API for monitoring and readiness probes."
)
def health_check() -> HealthResponse:
    """
    Health check endpoint:
    Used by load balancers, container orchestrators (e.g., Docker, Kubernetes),
    uptime monitors, and the frontend to verify backend availability.
    """
    return HealthResponse(
        status="healthy",
        app="HelpWise AI — ITSM Helpdesk",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        environment="development"
    )
