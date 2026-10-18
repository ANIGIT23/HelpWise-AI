from datetime import datetime
from enum import Enum
from typing import List, Optional
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


class TicketResponse(BaseModel):
    """Schema for individual ticket response returned to clients."""
    id: str = Field(..., description="Unique database document identifier or ID")
    ticket_number: str = Field(..., description="Human-readable ITSM ticket identifier (e.g. INC-1001)")
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus = TicketStatus.OPEN
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 UTC last update timestamp")


class TicketListResponse(BaseModel):
    """Schema for returning list of tickets along with active storage mode."""
    total: int
    tickets: List[TicketResponse]
    storage_mode: str = Field(..., description="Indicates whether MongoDB Atlas or In-Memory fallback is active")


class StorageStatusResponse(BaseModel):
    """Schema describing current database connection status."""
    connected: bool
    mode: str  # "mongodb_atlas" or "in_memory_fallback"
    database_name: str
    message: str
    instructions: Optional[str] = None
