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


class StorageStatusResponse(BaseModel):
    """Schema describing current database connection status."""
    connected: bool
    mode: str  # "mongodb_atlas" or "in_memory_fallback"
    database_name: str
    message: str
    instructions: Optional[str] = None
