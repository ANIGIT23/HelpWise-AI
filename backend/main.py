from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, status, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database
import rag
import chatbot
import diagnostics
import servicenow
from schemas import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketListResponse,
    DashboardStatsResponse,
    KBArticle,
    KBAskRequest,
    KBAskResponse,
    ChatRequest,
    ChatResponse,
    StorageStatusResponse,
    UserProfile,
    CatalogItem,
    ServiceRequestCreate,
    ServiceRequestStatusUpdate,
    ServiceRequestResponse,
    WorkSession,
    TimerActionRequest,
    TicketTimerStatusResponse,
    DiagnosticReport,
    KBArticleCreate,
    KBArticleUpdate,
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
    Returns 'degraded' when MongoDB Atlas was configured but is currently unreachable,
    so monitoring tools can distinguish a transient connection failure from a healthy
    in-memory-only development instance.
    """
    storage = await database.get_storage_status()
    # Atlas configured but unreachable -> degraded (writes are disabled)
    if storage.mode == "atlas_unreachable":
        health_status = "degraded"
    else:
        health_status = "healthy"
    return HealthResponse(
        status=health_status,
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
    try:
        return await database.get_dashboard_stats()
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate stats: {database._sanitize_error_message(exc)}"
        )


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
    requester: Optional[str] = Query(None, description="Filter by Requester"),
) -> TicketListResponse:
    """Fetches tickets with optional filters from MongoDB Atlas or in-memory fallback."""
    try:
        srch = search if isinstance(search, str) else None
        cat = category if isinstance(category, str) else None
        prio = priority if isinstance(priority, str) else None
        st = status_filter if isinstance(status_filter, str) else None
        asg = assignee if isinstance(assignee, str) else None
        req = requester if isinstance(requester, str) else None

        tickets = await database.get_all_tickets(
            search=srch,
            category=cat,
            priority=prio,
            status=st,
            assignee=asg,
            requester=req,
        )
        storage = await database.get_storage_status(check_live=False)
        return TicketListResponse(
            total=len(tickets),
            tickets=tickets,
            storage_mode=storage.mode,
        )
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
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
    """Creates a new ticket in MongoDB Atlas. Returns 503 if Atlas is configured but unreachable."""
    try:
        created_ticket = await database.create_ticket(payload)
        return created_ticket
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {database._sanitize_error_message(exc)}"
        )


@app.get(
    "/api/tickets/active-timer",
    tags=["Work Timers"],
    summary="Get active work timer for a specific agent",
)
async def get_active_timer_endpoint(agent: Optional[str] = Query(None)):
    sessions = await database.get_all_work_sessions(agent=agent)
    active = next((s for s in sessions if s.is_active), None)
    return {"active_timer": active}


@app.get(
    "/api/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["Tickets"],
    summary="Get Incident Details by ID",
    description="Retrieves a single incident by its ID or ticket number (e.g. INC-1001)."
)
async def get_ticket_endpoint(ticket_id: str) -> TicketResponse:
    """Retrieves full ticket details including activity history."""
    try:
        ticket = await database.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident '{ticket_id}' was not found in the database."
            )
        return ticket
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


@app.patch(
    "/api/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=["Tickets"],
    summary="Update Incident Status or Details",
    description="Updates ticket status, priority, assignee, or resolution notes, recording an activity log."
)
async def update_ticket_endpoint(ticket_id: str, payload: TicketUpdate) -> TicketResponse:
    """Updates incident fields and records lifecycle transition event in audit trail."""
    try:
        updated = await database.update_ticket(ticket_id, payload)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident '{ticket_id}' was not found to update."
            )
        return updated
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


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
    try:
        srch = search if isinstance(search, str) else None
        cat = category if isinstance(category, str) else None
        return await database.get_kb_articles(search=srch, category=cat)
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


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


@app.post(
    "/api/kb/chat",
    response_model=ChatResponse,
    tags=["Conversational AI"],
    summary="All-Rounder ITSM AI Assistant",
    description="Conversational assistant with intent routing for greetings, status lookup, service requests, incident intake, diagnostics, and grounded RAG knowledge search."
)
async def chat_kb_endpoint(
    payload: ChatRequest,
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> ChatResponse:
    safe_history = payload.history[-20:] if payload.history else []
    user_name = x_user_name or "Alex Morgan"
    user_role = x_user_role or "Employee"
    try:
        return await chatbot.handle_conversational_turn(
            message=payload.message,
            history=safe_history,
            user_name=user_name,
            user_role=user_role,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {database._sanitize_error_message(exc)}",
        )


# ── User Personas ────────────────────────────────────────────────────────────

@app.get(
    "/api/users/personas",
    response_model=List[UserProfile],
    tags=["Users"],
    summary="List available demo user personas",
)
async def list_personas_endpoint():
    return database.USER_PERSONAS


# ── Service Catalogue & Service Requests ─────────────────────────────────────

@app.get(
    "/api/catalog",
    response_model=List[CatalogItem],
    tags=["Service Catalog"],
    summary="List IT Service Catalogue Items",
)
@app.get(
    "/api/service-catalog",
    response_model=List[CatalogItem],
    tags=["Service Catalog"],
    summary="List IT Service Catalogue Items (alias)",
)
async def list_catalog_endpoint():
    return await database.get_catalog_items()


@app.get(
    "/api/service-requests",
    response_model=List[ServiceRequestResponse],
    tags=["Service Requests"],
    summary="List Service Requests with optional filters",
)
async def list_service_requests_endpoint(
    requester: Optional[str] = Query(None, description="Filter by requester name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by request status"),
):
    try:
        req = requester if isinstance(requester, str) else None
        st = status_filter if isinstance(status_filter, str) else None
        return await database.get_service_requests(requester=req, status=st)
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve service requests: {database._sanitize_error_message(exc)}"
        )


@app.post(
    "/api/service-requests",
    response_model=ServiceRequestResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Service Requests"],
    summary="Submit a new Service Request",
)
async def create_service_request_endpoint(
    payload: ServiceRequestCreate,
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
):
    try:
        actor = x_user_name or payload.requester
        return await database.create_service_request(payload, actor=actor)
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit service request: {database._sanitize_error_message(exc)}",
        )


@app.patch(
    "/api/service-requests/{req_id}/status",
    response_model=ServiceRequestResponse,
    tags=["Service Requests"],
    summary="Update Service Request status (Approve, Reject, Fulfill, Cancel)",
)
@app.patch(
    "/api/service-requests/{req_id}",
    response_model=ServiceRequestResponse,
    tags=["Service Requests"],
    summary="Update Service Request status (alias)",
)
async def update_service_request_status_endpoint(
    req_id: str,
    payload: ServiceRequestStatusUpdate,
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
):
    try:
        actor = payload.actor or x_user_name or "Approver"
        updated = await database.update_service_request_status(
            req_id,
            new_status=payload.status,
            notes=payload.get_notes(),
            actor=actor,
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found.")
        return updated
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


# ── Work Timers & Ticket Timeline ────────────────────────────────────────────

@app.post(
    "/api/tickets/{ticket_id}/timer/start",
    response_model=WorkSession,
    tags=["Work Timers"],
    summary="Start an active work timer for an agent on an incident",
)
@app.post(
    "/api/tickets/{ticket_id}/work-sessions/start",
    response_model=WorkSession,
    tags=["Work Timers"],
    summary="Start an active work timer (alias)",
)
async def start_work_timer_endpoint(
    ticket_id: str,
    payload: TimerActionRequest,
):
    try:
        return await database.start_work_timer(ticket_id, agent=payload.agent, note=payload.note)
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(db_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start timer: {database._sanitize_error_message(exc)}",
        )


@app.post(
    "/api/tickets/{ticket_id}/timer/stop",
    response_model=WorkSession,
    tags=["Work Timers"],
    summary="Stop the active work timer and calculate session duration",
)
@app.post(
    "/api/tickets/{ticket_id}/work-sessions/stop",
    response_model=WorkSession,
    tags=["Work Timers"],
    summary="Stop the active work timer (alias)",
)
async def stop_work_timer_endpoint(
    ticket_id: str,
    payload: TimerActionRequest,
):
    try:
        return await database.stop_work_timer(ticket_id, agent=payload.agent, note=payload.note)
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(db_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop timer: {database._sanitize_error_message(exc)}",
        )


@app.get(
    "/api/tickets/{ticket_id}/timer/status",
    response_model=TicketTimerStatusResponse,
    tags=["Work Timers"],
    summary="Get cumulative work time and active timer status for an incident",
)
@app.get(
    "/api/tickets/{ticket_id}/timer-status",
    response_model=TicketTimerStatusResponse,
    tags=["Work Timers"],
    summary="Get cumulative work time and active timer status (alias)",
)
async def get_ticket_timer_status_endpoint(
    ticket_id: str,
    agent: Optional[str] = Query(None),
):
    try:
        return await database.get_ticket_timer_status(ticket_id, agent=agent)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timer status: {database._sanitize_error_message(exc)}",
        )


@app.get(
    "/api/work-sessions",
    response_model=List[WorkSession],
    tags=["Work Timers"],
    summary="List all recorded work sessions for the Ticket Timeline",
)
async def get_all_work_sessions_endpoint(agent: Optional[str] = Query(None)):
    try:
        ag = agent if isinstance(agent, str) else None
        return await database.get_all_work_sessions(agent=ag)
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(db_err),
        )


# ── Self-Heal Diagnostics ────────────────────────────────────────────────────

@app.post(
    "/api/diagnostics/run",
    tags=["Diagnostics"],
    summary="Run all diagnostics suites and return aggregated report",
)
def run_all_diagnostics_endpoint():
    return diagnostics.run_all_diagnostics()


@app.get(
    "/api/diagnostics/network",
    response_model=DiagnosticReport,
    tags=["Diagnostics"],
    summary="Run safe network and DNS self-healing diagnostics",
)
def get_network_diagnostics_endpoint():
    return diagnostics.run_network_diagnostics()


@app.get(
    "/api/diagnostics/system",
    response_model=DiagnosticReport,
    tags=["Diagnostics"],
    summary="Run Python runtime, memory, and vector store diagnostics",
)
def get_system_diagnostics_endpoint():
    return diagnostics.run_system_diagnostics()


@app.get(
    "/api/diagnostics/disk",
    response_model=DiagnosticReport,
    tags=["Diagnostics"],
    summary="Run disk space and write permission diagnostics",
)
def get_disk_diagnostics_endpoint():
    return diagnostics.run_disk_diagnostics()


@app.get(
    "/api/diagnostics/servicenow",
    response_model=DiagnosticReport,
    tags=["Diagnostics"],
    summary="Run ServiceNow integration and Table API connectivity diagnostics",
)
def get_servicenow_diagnostics_endpoint():
    return diagnostics.run_servicenow_diagnostics()


# ── Dynamic Knowledge Base Management ────────────────────────────────────────

@app.post(
    "/api/kb",
    response_model=KBArticle,
    status_code=status.HTTP_201_CREATED,
    tags=["Knowledge Base"],
    summary="Create a new Knowledge Base article and refresh vector index",
)
@app.post(
    "/api/kb/articles",
    response_model=KBArticle,
    status_code=status.HTTP_201_CREATED,
    tags=["Knowledge Base"],
    summary="Create a new Knowledge Base article and refresh vector index (alias)",
)
async def create_kb_article_endpoint(payload: KBArticleCreate):
    try:
        art = await database.create_kb_article(payload)
        rag._chroma_fp = None  # Invalidate index fingerprint to trigger automatic rebuild
        return art
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(db_err))


@app.put(
    "/api/kb/{article_id}",
    response_model=KBArticle,
    tags=["Knowledge Base"],
    summary="Update an existing Knowledge Base article and refresh vector index",
)
async def update_kb_article_endpoint(article_id: str, payload: KBArticleUpdate):
    try:
        art = await database.update_kb_article(article_id, payload)
        if not art:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KB article not found")
        rag._chroma_fp = None  # Invalidate index fingerprint
        return art
    except database.DatabaseUnavailableError as db_err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(db_err))


# ── ServiceNow Integration ───────────────────────────────────────────────────

@app.get(
    "/api/servicenow/status",
    tags=["ServiceNow"],
    summary="Get ServiceNow integration and connection status",
)
def get_servicenow_status_endpoint(
    check_live: bool = Query(False, description="Perform a live probe to ServiceNow")
):
    return servicenow.get_servicenow_status(check_live=check_live)


@app.get(
    "/api/servicenow/verify",
    tags=["ServiceNow"],
    summary="Perform a live authentication and connectivity verification against ServiceNow",
)
async def verify_servicenow_endpoint():
    return await servicenow.verify_servicenow_connection()


@app.get(
    "/api/servicenow/incident/{number}",
    tags=["ServiceNow"],
    summary="Fetch an Incident from ServiceNow Table API by incident number",
)
async def get_servicenow_incident_endpoint(number: str):
    res = await servicenow.fetch_servicenow_incident(number)
    return res


@app.post(
    "/api/servicenow/sync/{ticket_id}",
    tags=["ServiceNow"],
    summary="Synchronize an incident with ServiceNow Table API (or Simulation Mode)",
)
async def sync_servicenow_endpoint(ticket_id: str):
    ticket = await database.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found to sync")
    return await servicenow.create_servicenow_incident(
        title=ticket.title,
        description=ticket.description,
        category=ticket.category.value if hasattr(ticket.category, "value") else str(ticket.category),
        priority=ticket.priority.value if hasattr(ticket.priority, "value") else str(ticket.priority),
        caller_id=ticket.requester,
        correlation_id=ticket.ticket_number,
    )

