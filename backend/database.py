import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from schemas import (
    TicketCreate,
    TicketResponse,
    TicketCategory,
    TicketPriority,
    TicketStatus,
    StorageStatusResponse,
)

# Load environment variables from backend/.env if present
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DATABASE_NAME = os.getenv("DATABASE_NAME", "helpwise_db").strip()

# Internal state tracking
_mongo_client = None
_db = None
_is_connected = False
_connection_message = "In-memory development fallback active. Configure MONGODB_URI in backend/.env for persistent Atlas storage."

# In-memory storage fallback with realistic initial ITSM sample tickets
_in_memory_tickets: List[Dict[str, Any]] = [
    {
        "id": "mem_1001",
        "ticket_number": "INC-1001",
        "title": "Cannot authenticate to corporate VPN via AnyConnect",
        "description": "User reports error 'Certificate Validation Failure (0x800B0109)' when attempting to connect from home network.",
        "category": TicketCategory.NETWORK.value,
        "priority": TicketPriority.HIGH.value,
        "status": TicketStatus.OPEN.value,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    },
    {
        "id": "mem_1002",
        "ticket_number": "INC-1002",
        "title": "Request developer license for JetBrains IDE",
        "description": "New joiner in backend engineering team requires IntelliJ IDEA Ultimate license for Python/FastAPI microservices.",
        "category": TicketCategory.ACCESS.value,
        "priority": TicketPriority.MEDIUM.value,
        "status": TicketStatus.IN_PROGRESS.value,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    },
]

_next_ticket_sequence = 1003


async def init_db() -> bool:
    """
    Attempts to connect to MongoDB Atlas if MONGODB_URI is provided.
    If not provided or if connection fails, safely enables in-memory fallback.
    """
    global _mongo_client, _db, _is_connected, _connection_message

    if not MONGODB_URI:
        _is_connected = False
        _connection_message = (
            "MONGODB_URI is not set in backend/.env. Running on in-memory storage fallback."
        )
        return False

    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        # Configure client with 2.5-second server selection timeout to avoid hanging on bad networks
        client = AsyncIOMotorClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=2500,
            connectTimeoutMS=2500,
        )
        # Verify connection with a lightweight ping command
        await client.admin.command("ping")

        _mongo_client = client
        _db = _mongo_client[DATABASE_NAME]
        _is_connected = True
        _connection_message = f"Successfully connected to MongoDB Atlas database: '{DATABASE_NAME}'"

        # Ensure index on ticket_number for fast lookups
        await _db.tickets.create_index("ticket_number", unique=True)
        return True

    except Exception as exc:
        _is_connected = False
        _connection_message = (
            f"Failed to connect to MongoDB Atlas ({str(exc)}). "
            f"Fell back to in-memory storage for seamless development."
        )
        return False


async def get_storage_status() -> StorageStatusResponse:
    """Returns metadata about the active storage layer."""
    instructions_text = (
        "To connect MongoDB Atlas:\n"
        "1. Create a free M0 cluster at https://cloud.mongodb.com\n"
        "2. Create a Database User (Username/Password)\n"
        "3. Whitelist Network Access IP (add 0.0.0.0/0 for anywhere)\n"
        "4. Copy the connection string into backend/.env: MONGODB_URI=mongodb+srv://...\n"
        "5. Restart the backend server."
    )
    return StorageStatusResponse(
        connected=_is_connected,
        mode="mongodb_atlas" if _is_connected else "in_memory_fallback",
        database_name=DATABASE_NAME if _is_connected else "local_memory",
        message=_connection_message,
        instructions=instructions_text if not _is_connected else None,
    )


async def create_ticket(ticket_data: TicketCreate) -> TicketResponse:
    """
    Creates a new ITSM ticket in MongoDB Atlas (or in-memory store if Atlas is offline).
    Generates an incremental ticket identifier (e.g. INC-1003).
    """
    global _next_ticket_sequence
    now_iso = datetime.utcnow().isoformat() + "Z"

    if _is_connected and _db is not None:
        # Generate ticket sequence count in MongoDB
        count = await _db.tickets.count_documents({})
        ticket_number = f"INC-{1001 + count}"

        doc = {
            "ticket_number": ticket_number,
            "title": ticket_data.title.strip(),
            "description": ticket_data.description.strip(),
            "category": ticket_data.category.value,
            "priority": ticket_data.priority.value,
            "status": TicketStatus.OPEN.value,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        result = await _db.tickets.insert_one(doc)
        return TicketResponse(
            id=str(result.inserted_id),
            ticket_number=ticket_number,
            title=doc["title"],
            description=doc["description"],
            category=TicketCategory(doc["category"]),
            priority=TicketPriority(doc["priority"]),
            status=TicketStatus(doc["status"]),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )

    # In-memory storage fallback
    ticket_number = f"INC-{_next_ticket_sequence}"
    _next_ticket_sequence += 1

    doc = {
        "id": f"mem_{_next_ticket_sequence - 1}",
        "ticket_number": ticket_number,
        "title": ticket_data.title.strip(),
        "description": ticket_data.description.strip(),
        "category": ticket_data.category.value,
        "priority": ticket_data.priority.value,
        "status": TicketStatus.OPEN.value,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    # Prepend to display newest first
    _in_memory_tickets.insert(0, doc)

    return TicketResponse(
        id=doc["id"],
        ticket_number=doc["ticket_number"],
        title=doc["title"],
        description=doc["description"],
        category=TicketCategory(doc["category"]),
        priority=TicketPriority(doc["priority"]),
        status=TicketStatus(doc["status"]),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def get_all_tickets() -> List[TicketResponse]:
    """Retrieves all tickets sorted by creation time descending (newest first)."""
    if _is_connected and _db is not None:
        cursor = _db.tickets.find({}).sort("created_at", -1)
        tickets: List[TicketResponse] = []
        async for doc in cursor:
            tickets.append(
                TicketResponse(
                    id=str(doc["_id"]),
                    ticket_number=doc["ticket_number"],
                    title=doc["title"],
                    description=doc["description"],
                    category=TicketCategory(doc["category"]),
                    priority=TicketPriority(doc["priority"]),
                    status=TicketStatus(doc["status"]),
                    created_at=doc["created_at"],
                    updated_at=doc["updated_at"],
                )
            )
        return tickets

    # Return in-memory tickets
    return [
        TicketResponse(
            id=t["id"],
            ticket_number=t["ticket_number"],
            title=t["title"],
            description=t["description"],
            category=TicketCategory(t["category"]),
            priority=TicketPriority(t["priority"]),
            status=TicketStatus(t["status"]),
            created_at=t["created_at"],
            updated_at=t["updated_at"],
        )
        for t in _in_memory_tickets
    ]
