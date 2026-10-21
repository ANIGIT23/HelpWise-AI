from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, status, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database
import rag
from schemas import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketListResponse,
    DashboardStatsResponse,
    KBArticle,
    KBAskRequest,
    KBAskResponse,
    StorageStatusResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Executes database initialization on startup and graceful teardown on shutdown.
    """
    await database.init_db()
    yield
    await database.close_db()


# Initialize FastAPI application
app = FastAPI(
    title="HelpWise AI — ITSM Helpdesk Backend",
    description="Core REST API service for HelpWise AI ITSM Helpdesk application",
    version="1.1.0",
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
        "stats_api": "/api/stats",
        "kb_api": "/api/kb",
        "kb_ask_api": "/api/kb/ask",
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
        version="1.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
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


@app.get(
    "/api/stats",
    response_model=DashboardStatsResponse,
    tags=["Dashboard"],
    summary="Get Operational Dashboard Statistics",
    description="Calculates real-time incident metrics, status breakdown, category distribution, and priority counts."
)
async def get_stats_endpoint() -> DashboardStatsResponse:
    """Returns operational KPIs calculated from live incident records."""
    return await database.get_dashboard_stats()


@app.get(
    "/api/tickets",
    response_model=TicketListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Tickets"],
    summary="Retrieve all ITSM Tickets",
    description="Returns submitted incident tickets with optional search and filter criteria."
)
async def list_tickets_endpoint(
    search: Optional[str] = Query(None, description="Search keyword in ticket ID, title, or description"),
    category: Optional[str] = Query(None, description="Filter by Category"),
    priority: Optional[str] = Query(None, description="Filter by Priority"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by Status"),
    assignee: Optional[str] = Query(None, description="Filter by Assignee"),
) -> TicketListResponse:
    """Fetches tickets with optional filters from MongoDB Atlas or in-memory fallback."""
    try:
        srch = search if isinstance(search, str) else None
        cat = category if isinstance(category, str) else None
        prio = priority if isinstance(priority, str) else None
        st = status_filter if isinstance(status_filter, str) else None
        asg = assignee if isinstance(assignee, str) else None

        tickets = await database.get_all_tickets(
            search=srch,
            category=cat,
            priority=prio,
            status=st,
            assignee=asg,
        )
        storage = await database.get_storage_status()
        return TicketListResponse(
            total=len(tickets),
            tickets=tickets,
            storage_mode=storage.mode,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tickets: {database._sanitize_error_message(exc)}"
        )


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
            detail=f"Failed to create ticket: {database._sanitize_error_message(exc)}"
        )


@app.get(
    "/api/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["Tickets"],
    summary="Get Incident Details by ID",
    description="Retrieves a single incident by its ID or ticket number (e.g. INC-1001)."
)
async def get_ticket_endpoint(ticket_id: str) -> TicketResponse:
    """Retrieves full ticket details including activity history."""
    ticket = await database.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{ticket_id}' was not found in the database."
        )
    return ticket


@app.patch(
    "/api/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["Tickets"],
    summary="Update Incident Status or Details",
    description="Updates ticket status, priority, assignee, or resolution notes, recording an activity log."
)
async def update_ticket_endpoint(ticket_id: str, payload: TicketUpdate) -> TicketResponse:
    """Updates incident fields and records lifecycle transition event in audit trail."""
    updated = await database.update_ticket(ticket_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{ticket_id}' was not found to update."
        )
    return updated


@app.get(
    "/api/kb",
    response_model=List[KBArticle],
    tags=["Knowledge Base"],
    summary="List Knowledge Base Articles",
    description="Retrieves searchable demonstration IT troubleshooting articles."
)
async def list_kb_endpoint(
    search: Optional[str] = Query(None, description="Search keyword in title, content, or tags"),
    category: Optional[str] = Query(None, description="Filter by Category"),
) -> List[KBArticle]:
    """Returns demonstration Knowledge Base articles."""
    srch = search if isinstance(search, str) else None
    cat = category if isinstance(category, str) else None
    return await database.get_kb_articles(search=srch, category=cat)


@app.post(
    "/api/kb/ask",
    response_model=KBAskResponse,
    tags=["Knowledge Base"],
    summary="Ask a question against knowledge-base articles",
    description=(
        "Retrieves existing KB articles with MiniLM embeddings in ChromaDB "
        "(falls back to TF-IDF if embeddings cannot load). Answers are copied from articles; no generative LLM."
    ),
)
async def ask_kb_endpoint(payload: KBAskRequest) -> KBAskResponse:
    """Retrieve matching articles, then compose a labelled fallback answer from them."""
    try:
        articles = await database.get_kb_articles()
        return rag.answer_question(payload.question, articles)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search knowledge base: {database._sanitize_error_message(exc)}",
        )
