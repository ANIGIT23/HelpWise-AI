from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class TicketCategory(str, Enum):
    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    NETWORK = "Network"
    ACCESS = "Access"
    OTHER = "Other"


class TicketPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class TicketStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class ActivityLogEntry(BaseModel):
    """Represents a timestamped action in the incident audit trail."""
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    actor: str = Field(default="System", description="User or agent who performed the action")
    action: str = Field(..., description="Type of event: Created, Status Change, Reassigned, Note")
    note: str = Field(..., description="Human-readable description of the change")


class TicketCreate(BaseModel):
    """Schema for incoming ticket submission from the frontend form."""
    title: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Concise summary of the IT issue",
        examples=["Cannot connect to corporate VPN"]
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed explanation of the technical issue, error messages, and reproduction steps",
        examples=["Getting error 'TLS Handshake Failed 0x800' when trying to connect to AnyConnect."]
    )
    category: TicketCategory = Field(
        ...,
        description="Classification of the IT problem"
    )
    priority: TicketPriority = Field(
        ...,
        description="Urgency and business impact of the ticket"
    )
    assignee: Optional[str] = Field(
        default="Unassigned",
        description="Assigned support agent name"
    )
    requester: Optional[str] = Field(
        default="IT Helpdesk User",
        description="Name or department of the user reporting the incident"
    )


class TicketUpdate(BaseModel):
    """Schema for updating an existing ticket's lifecycle state or metadata."""
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    category: Optional[TicketCategory] = None
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None
    assignee: Optional[str] = None
    resolution_notes: Optional[str] = None
    updated_by: Optional[str] = "IT Support Agent"


class TicketResponse(BaseModel):
    """Schema for individual ticket response returned to clients."""
    id: str = Field(..., description="Unique database document identifier or ID")
    ticket_number: str = Field(..., description="Human-readable ITSM ticket identifier (e.g. INC-1001)")
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus = TicketStatus.OPEN
    assignee: str = "Unassigned"
    requester: str = "IT Helpdesk User"
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 UTC last update timestamp")
    activity_history: List[ActivityLogEntry] = Field(default_factory=list)
    resolution_notes: Optional[str] = None


class TicketListResponse(BaseModel):
    """Schema for returning list of tickets along with active storage mode."""
    total: int
    tickets: List[TicketResponse]
    storage_mode: str = Field(..., description="Indicates whether MongoDB Atlas or In-Memory fallback is active")


class DashboardStatsResponse(BaseModel):
    """Operational metrics calculated from active incident records."""
    total: int
    open: int
    in_progress: int
    resolved: int
    closed: int
    high_critical: int
    by_category: Dict[str, int]
    by_priority: Dict[str, int]
    by_status: Dict[str, int]


class KBArticle(BaseModel):
    """Demonstration Knowledge Base article schema."""
    id: str
    title: str
    category: str
    read_time: str
    excerpt: str
    content: str
    tags: List[str]
    updated_at: str


class KBAskRequest(BaseModel):
    """User question against the existing IT knowledge base."""
    question: str = Field(..., min_length=3, max_length=500, description="IT support question")


class KBAskHit(BaseModel):
    """One ranked knowledge-base article used as retrieval context."""
    id: str
    title: str
    category: str
    excerpt: str
    content: str
    tags: List[str]
    score: float


class KBAskResponse(BaseModel):
    """Retrieve-then-compose response. llm_used is always false until an LLM is wired."""
    question: str
    answer: str
    matched_articles: List[KBAskHit]
    retrieval_method: str
    generation_mode: str
    llm_used: bool
    vector_database: str
    disclaimer: str


# ── Conversational Chat ──────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    """A single turn in a conversation (role = 'user' | 'assistant')."""
    role: str = Field(..., pattern="^(user|assistant)$", description="Message author: 'user' or 'assistant'")
    content: str = Field(..., min_length=1, max_length=2000, description="Message text")


class ChatRequest(BaseModel):
    """
    Request body for POST /api/kb/chat.
    Sends the latest user message plus a bounded window of prior turns for context.
    """
    message: str = Field(..., min_length=3, max_length=1000, description="The user's current message")
    history: List[ChatMessage] = Field(
        default_factory=list,
        max_length=20,
        description="Recent conversation turns (oldest first, max 20 items)"
    )


class ChatResponse(BaseModel):
    """Response for a single chat turn."""
    message: str = Field(..., description="Assistant's reply text")
    matched_articles: List[KBAskHit] = Field(default_factory=list)
    generation_mode: str = Field(..., description="How the answer was produced")
    llm_used: bool
    vector_database: str
    has_answer: bool = Field(..., description="True when a verified KB article was found")
    intent: Optional[str] = Field(default="knowledge_search", description="Classified user intent")
    action_proposed: Optional[Dict] = Field(default=None, description="Proposed action requiring confirmation")
    action_result: Optional[Dict] = Field(default=None, description="Result of confirmed action")


class StorageStatusResponse(BaseModel):
    """Schema describing current database connection status."""
    connected: bool
    mode: str  # "mongodb_atlas" or "in_memory_fallback"
    database_name: str
    message: str
    instructions: Optional[str] = None


# ── User Identity & Personas ─────────────────────────────────────────────────

class UserRole(str, Enum):
    EMPLOYEE = "Employee"
    AGENT = "Support Agent"
    ADMIN = "Administrator"


class UserProfile(BaseModel):
    username: str
    name: str
    email: str
    role: UserRole
    department: str
    avatar: str


# ── Service Requests & Catalogue ─────────────────────────────────────────────

class RequestCategory(str, Enum):
    SOFTWARE = "Software & Licenses"
    ACCESS = "Access & Permissions"
    HARDWARE = "Hardware & Equipment"
    NETWORK = "VPN & Network"
    OTHER = "Other IT Services"


class RequestStatus(str, Enum):
    SUBMITTED = "Submitted"
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    IN_PROGRESS = "In Progress"
    FULFILLED = "Fulfilled"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"


class CatalogItem(BaseModel):
    id: str
    name: str
    category: RequestCategory
    description: str
    requires_approval: bool = True
    estimated_delivery: str
    icon: str


class ServiceRequestCreate(BaseModel):
    catalog_item_id: str
    item_name: str
    category: RequestCategory
    # Accept both field names from the frontend
    justification: Optional[str] = Field(default=None, min_length=5, max_length=1000)
    business_justification: Optional[str] = Field(default=None, min_length=5, max_length=1000)
    additional_info: Optional[str] = None
    additional_details: Optional[str] = None  # Frontend alias for additional_info
    requester: str = Field(default="Alex Morgan")
    requester_email: Optional[str] = None
    department: Optional[str] = "Engineering"

    def get_justification(self) -> str:
        return (self.business_justification or self.justification or "").strip()


class ServiceRequestStatusUpdate(BaseModel):
    status: RequestStatus
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None  # Frontend alias for notes
    actor: Optional[str] = None

    def get_notes(self) -> Optional[str]:
        return self.rejection_reason or self.notes


class ServiceRequestResponse(BaseModel):
    id: str
    request_number: str
    catalog_item_id: str
    item_name: str
    category: str
    justification: str
    business_justification: Optional[str] = None
    additional_info: Optional[str] = None
    additional_details: Optional[str] = None
    requester: str
    department: str
    status: RequestStatus
    requires_approval: bool
    approver: Optional[str] = None
    approval_notes: Optional[str] = None
    created_at: str
    updated_at: str
    activity_history: List[ActivityLogEntry] = Field(default_factory=list)



# ── Work Timers & Ticket Timeline ────────────────────────────────────────────

class WorkSession(BaseModel):
    id: str
    ticket_id: str
    ticket_number: str
    agent: str
    start_time: str
    stop_time: Optional[str] = None
    duration_seconds: int = 0
    duration_minutes: int = 0  # Pre-computed minutes for frontend convenience
    is_active: bool = True
    note: Optional[str] = None


class TimerActionRequest(BaseModel):
    agent: str = Field(..., description="Agent username or name")
    note: Optional[str] = None


class TicketTimerStatusResponse(BaseModel):
    ticket_id: str
    active_session: Optional[WorkSession] = None
    total_duration_seconds: int = 0
    total_duration_formatted: str = "0m"
    total_duration_minutes: int = 0  # Pre-computed minutes for frontend
    is_agent_active: bool = False      # True when current agent has this ticket's timer running
    sessions_count: int = 0
    sessions: List[WorkSession] = Field(default_factory=list)


# ── Self-Heal Diagnostics ────────────────────────────────────────────────────

class DiagnosticStepResult(BaseModel):
    name: str
    target: str
    status: str  # "passed", "failed", "warning"
    latency_ms: Optional[float] = None
    details: str
    remediation: Optional[str] = None


class DiagnosticReport(BaseModel):
    workflow: str  # "network", "system", "disk"
    overall_status: str
    executed_at: str
    checks_run: int
    steps: List[DiagnosticStepResult]
    escalation_recommended: bool
    escalation_reason: Optional[str] = None


# ── KB Article Management ────────────────────────────────────────────────────

class KBArticleCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    category: str
    read_time: str = "3 min"
    excerpt: str = Field(..., min_length=10, max_length=300)
    content: str = Field(..., min_length=20)
    tags: List[str] = Field(default_factory=list)


class KBArticleUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    read_time: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None

