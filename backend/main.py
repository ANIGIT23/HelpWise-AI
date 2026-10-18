from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List
from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database
from schemas import (
    TicketCreate,
    TicketResponse,
    TicketListResponse,
    StorageStatusResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Executes database initialization on startup.
    """
    await database.init_db()
    yield
    # Cleanup logic (if any) executes on shutdown


# Initialize FastAPI application
app = FastAPI(
    title="HelpWise AI — ITSM Helpdesk Backend",
    description="Core REST API service for HelpWise AI ITSM Helpdesk application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
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
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic schema for health response
class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    timestamp: str
    environment: str
    storage_mode: str
    database_connected: bool


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
        "tickets_api": "/api/tickets",
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
async def health_check() -> HealthResponse:
    """
    Health check endpoint:
    Verifies that the backend process is running and reports active storage mode.
    """
    storage = await database.get_storage_status()
    return HealthResponse(
        status="healthy",
        app="HelpWise AI — ITSM Helpdesk",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        environment="development",
        storage_mode=storage.mode,
        database_connected=storage.connected,
    )


@app.get(
    "/api/storage-status",
    response_model=StorageStatusResponse,
    tags=["Database"],
    summary="Get Database Storage Status",
    description="Returns whether MongoDB Atlas or In-Memory fallback storage is currently active."
)
async def get_storage_status() -> StorageStatusResponse:
    """Provides transparent metadata about the database layer."""
    return await database.get_storage_status()


@app.post(
    "/api/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tickets"],
    summary="Create a new ITSM Ticket",
    description="Validates ticket payload, creates an incident ticket, and returns the persisted record."
)
async def create_ticket_endpoint(payload: TicketCreate) -> TicketResponse:
    """Creates a new ticket in MongoDB Atlas (or in-memory store if Atlas is offline)."""
    try:
        created_ticket = await database.create_ticket(payload)
        return created_ticket
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {str(exc)}"
        )


@app.get(
    "/api/tickets",
    response_model=TicketListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Tickets"],
    summary="Retrieve all ITSM Tickets",
    description="Returns all submitted incident tickets sorted with newest first."
)
async def list_tickets_endpoint() -> TicketListResponse:
    """Fetches all tickets from MongoDB Atlas or in-memory fallback."""
    try:
        tickets = await database.get_all_tickets()
        storage = await database.get_storage_status()
        return TicketListResponse(
            total=len(tickets),
            tickets=tickets,
            storage_mode=storage.mode,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tickets: {str(exc)}"
        )
