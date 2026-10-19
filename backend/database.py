import os
import re
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

from schemas import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketCategory,
    TicketPriority,
    TicketStatus,
    ActivityLogEntry,
    DashboardStatsResponse,
    KBArticle,
    StorageStatusResponse,
)

# Load environment variables from backend/.env if present
load_dotenv()

# Logger configuration
logger = logging.getLogger("helpwise.database")

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DATABASE_NAME = os.getenv("DATABASE_NAME", "helpwise_ai").strip()

# Internal state tracking
_mongo_client = None
_db = None
_is_connected = False
_connection_message = "In-memory development fallback active. Configure MONGODB_URI in backend/.env for persistent Atlas storage."

# Demonstration Knowledge Base Articles (used for seeding and fallback)
_DEMO_KB_ARTICLES: List[Dict[str, Any]] = [
    {
        "id": "kb-101",
        "title": "Troubleshooting Cisco AnyConnect VPN Certificate Errors",
        "category": "Network",
        "read_time": "3 min",
        "excerpt": "Steps to resolve 'Certificate Validation Failure (0x800B0109)' when authenticating to the corporate VPN.",
        "content": (
            "1. Open the Windows Certificate Manager (certmgr.msc).\n"
            "2. Navigate to 'Trusted Root Certification Authorities' > 'Certificates'.\n"
            "3. Verify that 'HelpWise Enterprise Root CA 2026' is present.\n"
            "4. If missing, download and install the company root profile from the internal portal (https://pki.corp.local).\n"
            "5. Restart Cisco AnyConnect Secure Client and reconnect.\n"
            "6. If the problem persists, flush DNS cache using 'ipconfig /flushdns' in PowerShell."
        ),
        "tags": ["VPN", "AnyConnect", "Security", "Network"],
        "updated_at": "2026-10-18T10:00:00Z",
    },
    {
        "id": "kb-102",
        "title": "Requesting and Activating JetBrains / IDE Developer Licenses",
        "category": "Access",
        "read_time": "2 min",
        "excerpt": "Standard operating procedure for new engineering joiners to obtain IntelliJ, PyCharm, or WebStorm enterprise seats.",
        "content": (
            "1. Submit an Access incident ticket with category 'Access' and title 'JetBrains Developer License Request'.\n"
            "2. Ensure your manager has approved the request via email or Slack ticket thread.\n"
            "3. The IT Helpdesk team will provision a JetBrains Account invitation within 4 business hours.\n"
            "4. Open your IDE > Help > Register > Select 'JB Account' and sign in with your corporate SSO email."
        ),
        "tags": ["License", "JetBrains", "IDE", "Onboarding"],
        "updated_at": "2026-10-15T14:30:00Z",
    },
    {
        "id": "kb-103",
        "title": "Resolving Microsoft Outlook 365 Startup Crash (Error 0xc0000005)",
        "category": "Software",
        "read_time": "4 min",
        "excerpt": "Fix memory access violation crashes in Outlook 365 following Windows Cumulative Updates.",
        "content": (
            "1. Launch Outlook in Safe Mode: Hold CTRL while clicking the Outlook icon or run 'outlook.exe /safe'.\n"
            "2. If Outlook starts in safe mode, navigate to File > Options > Add-ins > COM Add-ins.\n"
            "3. Disable third-party anti-spam or sync add-ins.\n"
            "4. Delete corrupt temporary profile cache located at %localappdata%\\Microsoft\\Outlook\\RoamCache.\n"
            "5. Run Office Quick Repair via Settings > Apps > Installed Apps > Microsoft 365 Apps > Modify."
        ),
        "tags": ["Outlook", "Office365", "Crash", "Email"],
        "updated_at": "2026-10-17T09:15:00Z",
    },
    {
        "id": "kb-104",
        "title": "Self-Service Multi-Factor Authentication (MFA) Reset Procedure",
        "category": "Access",
        "read_time": "3 min",
        "excerpt": "How to register a replacement phone or authenticator app when locked out of corporate Okta / Entra ID.",
        "content": (
            "1. Visit the company identity portal from a registered corporate laptop: https://auth.corp.local/recovery.\n"
            "2. Complete secondary identity verification using your registered SMS or Hardware FIDO key.\n"
            "3. Click 'Reset Authenticator App' to generate a fresh QR code.\n"
            "4. Scan the code using Google Authenticator or Microsoft Authenticator.\n"
            "5. If you do not have any backup method registered, call the emergency IT Service Desk line (+1-800-HELPDESK)."
        ),
        "tags": ["MFA", "Okta", "Authentication", "Security"],
        "updated_at": "2026-10-12T16:00:00Z",
    },
    {
        "id": "kb-105",
        "title": "Corporate 802.1X Wi-Fi Connection Guide (HelpWise-Secure)",
        "category": "Hardware",
        "read_time": "2 min",
        "excerpt": "Configure WPA3-Enterprise 802.1X EAP-TLS profile on laptops, tablets, and mobile devices.",
        "content": (
            "1. Select the SSID 'HelpWise-Secure' from your network list.\n"
            "2. Choose EAP Method: PEAP or TLS.\n"
            "3. Phase 2 Authentication: MSCHAPv2.\n"
            "4. CA Certificate: 'Use system certificates' (Domain: corp.helpwise.ai).\n"
            "5. Identity: Enter your corporate username and domain password.\n"
            "6. Accept the radius server fingerprint on initial connection."
        ),
        "tags": ["Wi-Fi", "Network", "Hardware", "Mobile"],
        "updated_at": "2026-10-10T11:45:00Z",
    },
]

# In-memory storage fallback with realistic initial ITSM sample tickets
_in_memory_tickets: List[Dict[str, Any]] = [
    {
        "id": "mem_1001",
        "ticket_number": "INC-1001",
        "title": "Cannot authenticate to corporate VPN via AnyConnect",
        "description": "User reports error 'Certificate Validation Failure (0x800B0109)' when attempting to connect from home network. Needs root CA certificate installed.",
        "category": TicketCategory.NETWORK.value,
        "priority": TicketPriority.HIGH.value,
        "status": TicketStatus.IN_PROGRESS.value,
        "assignee": "Sarah Chen",
        "requester": "DevOps Engineering",
        "created_at": "2026-10-18T12:00:00.000000Z",
        "updated_at": "2026-10-18T14:30:00.000000Z",
        "resolution_notes": None,
        "activity_history": [
            {
                "timestamp": "2026-10-18T12:00:00.000000Z",
                "actor": "DevOps Engineering",
                "action": "Created",
                "note": "Incident submitted via web portal",
            },
            {
                "timestamp": "2026-10-18T14:30:00.000000Z",
                "actor": "Sarah Chen",
                "action": "Status Change",
                "note": "Moved status from Open to In Progress. Investigating PKI certificate deployment.",
            },
        ],
    },
    {
        "id": "mem_1002",
        "ticket_number": "INC-1002",
        "title": "Request developer license for JetBrains IDE",
        "description": "New joiner in backend engineering team requires IntelliJ IDEA Ultimate license for Python/FastAPI microservices.",
        "category": TicketCategory.ACCESS.value,
        "priority": TicketPriority.MEDIUM.value,
        "status": TicketStatus.OPEN.value,
        "assignee": "Alex Morgan",
        "requester": "Priya Sharma (Finance Tech)",
        "created_at": "2026-10-18T13:15:00.000000Z",
        "updated_at": "2026-10-18T13:15:00.000000Z",
        "resolution_notes": None,
        "activity_history": [
            {
                "timestamp": "2026-10-18T13:15:00.000000Z",
                "actor": "Priya Sharma",
                "action": "Created",
                "note": "Incident submitted with manager approval attached",
            }
        ],
    },
    {
        "id": "mem_1003",
        "ticket_number": "INC-1003",
        "title": "Outlook desktop app crashes on startup with error 0xc0000005",
        "description": "After the latest Windows security update, Microsoft Outlook crashes within 5 seconds of opening. Tested in safe mode; add-in collision suspected.",
        "category": TicketCategory.SOFTWARE.value,
        "priority": TicketPriority.CRITICAL.value,
        "status": TicketStatus.OPEN.value,
        "assignee": "Unassigned",
        "requester": "Executive Staff",
        "created_at": "2026-10-18T15:45:00.000000Z",
        "updated_at": "2026-10-18T15:45:00.000000Z",
        "resolution_notes": None,
        "activity_history": [
            {
                "timestamp": "2026-10-18T15:45:00.000000Z",
                "actor": "Executive Staff",
                "action": "Created",
                "note": "Critical escalation created for email client failure",
            }
        ],
    },
    {
        "id": "mem_1004",
        "ticket_number": "INC-1004",
        "title": "Docking station USB-C display link flickering in Conference Room B",
        "description": "Dell WD19TBS dual HDMI outputs intermittently disconnect when laptop draws high power. Firmware update or replacement cable needed.",
        "category": TicketCategory.HARDWARE.value,
        "priority": TicketPriority.LOW.value,
        "status": TicketStatus.RESOLVED.value,
        "assignee": "David Miller",
        "requester": "Facilities Lead",
        "created_at": "2026-10-17T09:00:00.000000Z",
        "updated_at": "2026-10-17T16:20:00.000000Z",
        "resolution_notes": "Replaced faulty Thunderbolt 4 cable and updated dock firmware to v01.00.24. Tested with dual 4K monitors successfully.",
        "activity_history": [
            {
                "timestamp": "2026-10-17T09:00:00.000000Z",
                "actor": "Facilities Lead",
                "action": "Created",
                "note": "Incident logged for conference room equipment",
            },
            {
                "timestamp": "2026-10-17T16:20:00.000000Z",
                "actor": "David Miller",
                "action": "Status Change",
                "note": "Resolved ticket: Cable swapped and firmware updated.",
            },
        ],
    },
]

_next_ticket_sequence = 1005


def _sanitize_error_message(err: Exception) -> str:
    """
    Sanitizes any database error message to prevent accidental leakage
    of credentials, connection strings, usernames, or passwords.
    """
    raw = str(err)
    # Strip any MongoDB URI pattern including user:pass or server hosts
    redacted = re.sub(r"mongodb(\+srv)?://[^\s@]+@[^\s/]+", "mongodb+srv://<REDACTED>@<CLUSTER>", raw)
    redacted = re.sub(r"mongodb(\+srv)?://[^\s]+", "mongodb+srv://<REDACTED>", redacted)

    err_type = type(err).__name__
    if "ServerSelectionTimeoutError" in err_type or "Timeout" in err_type:
        return "Connection timed out. Please verify that your current IP address is added to MongoDB Atlas Network Access."
    elif "OperationFailure" in err_type and ("Authentication" in raw or "auth" in raw.lower()):
        return "Authentication failed. Please verify the database username and password in MONGODB_URI."
    elif "ConfigurationError" in err_type:
        return "Invalid MongoDB connection string configuration."
    return f"{err_type}: {redacted[:100]}"


def _dict_to_ticket_response(doc: Dict[str, Any]) -> TicketResponse:
    """Helper to convert stored dictionary or Mongo document to TicketResponse."""
    return TicketResponse(
        id=str(doc.get("_id", doc.get("id"))),
        ticket_number=doc["ticket_number"],
        title=doc["title"],
        description=doc["description"],
        category=TicketCategory(doc["category"]),
        priority=TicketPriority(doc["priority"]),
        status=TicketStatus(doc["status"]),
        assignee=doc.get("assignee", "Unassigned"),
        requester=doc.get("requester", "IT Helpdesk User"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        resolution_notes=doc.get("resolution_notes"),
        activity_history=[
            ActivityLogEntry(**entry)
            for entry in doc.get("activity_history", [])
        ],
    )


async def _ensure_indexes_and_seed() -> None:
    """
    Creates unique indexes and seeds initial demonstration tickets & KB articles
    in MongoDB Atlas if the collections are currently empty (idempotent, 0 duplicates).
    """
    if _db is None:
        return

    try:
        # 1. Unique index on ticket_number
        await _db.tickets.create_index("ticket_number", unique=True)
        # 2. Unique index on KB article ID
        await _db.knowledge_base.create_index("id", unique=True)

        # 3. Seed demo tickets if empty
        ticket_count = await _db.tickets.count_documents({})
        if ticket_count == 0:
            for item in _in_memory_tickets:
                doc = dict(item)
                # Remove in-memory "id" key so Mongo generates native _id
                doc.pop("id", None)
                await _db.tickets.insert_one(doc)
            logger.info("Successfully seeded demo ITSM tickets into MongoDB Atlas")

        # 4. Seed demo Knowledge Base articles if empty
        kb_count = await _db.knowledge_base.count_documents({})
        if kb_count == 0:
            for article in _DEMO_KB_ARTICLES:
                doc = dict(article)
                await _db.knowledge_base.insert_one(doc)
            logger.info("Successfully seeded demo KB articles into MongoDB Atlas")

    except Exception as exc:
        sanitized = _sanitize_error_message(exc)
        logger.warning(f"Note during index/seed check: {sanitized}")


async def init_db() -> bool:
    """
    Attempts to connect to MongoDB Atlas if MONGODB_URI is provided.
    If not provided, placeholder, or if connection fails, safely enables in-memory fallback.
    Never exposes credentials or secrets in logs, messages, or exceptions.
    """
    global _mongo_client, _db, _is_connected, _connection_message

    # Re-read environment variables in case .env was modified
    load_dotenv(override=True)
    uri = os.getenv("MONGODB_URI", "").strip()
    db_name = os.getenv("DATABASE_NAME", "helpwise_ai").strip()

    # Check if MONGODB_URI is empty or still contains placeholder
    is_placeholder = (
        not uri
        or uri == "your_connection_string_here"
        or uri.startswith("your_")
        or "<username>" in uri
    )

    if is_placeholder:
        _is_connected = False
        _mongo_client = None
        _db = None
        _connection_message = (
            "MONGODB_URI is not configured in backend/.env. Running on in-memory storage fallback."
        )
        return False

    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
        )
        # Verify cluster accessibility via ping command
        await client.admin.command("ping")

        _mongo_client = client
        _db = _mongo_client[db_name]
        _is_connected = True
        _connection_message = f"Successfully connected to MongoDB Atlas database: '{db_name}'"

        # Ensure indexes and initial demonstration data are present
        await _ensure_indexes_and_seed()
        return True

    except Exception as exc:
        _is_connected = False
        _mongo_client = None
        _db = None
        sanitized_err = _sanitize_error_message(exc)
        _connection_message = (
            f"Failed to connect to MongoDB Atlas ({sanitized_err}). "
            f"Fell back to in-memory storage for seamless development."
        )
        logger.warning(f"MongoDB connection attempt failed: {sanitized_err}")
        return False


async def close_db() -> None:
    """Closes active MongoDB client connection cleanly during shutdown."""
    global _mongo_client, _db, _is_connected
    if _mongo_client is not None:
        try:
            _mongo_client.close()
        except Exception:
            pass
        _mongo_client = None
        _db = None
        _is_connected = False


async def get_storage_status() -> StorageStatusResponse:
    """Returns metadata about the active storage layer."""
    db_name = os.getenv("DATABASE_NAME", "helpwise_ai").strip()
    instructions_text = (
        "To connect MongoDB Atlas:\n"
        "1. Open MongoDB Atlas (cloud.mongodb.com) and navigate to your cluster 'HelpWiseCluster'.\n"
        "2. Ensure your current IP address is added in Network Access.\n"
        "3. Copy your connection string and add it to backend/.env: MONGODB_URI=...\n"
        "4. Restart the backend server."
    )
    return StorageStatusResponse(
        connected=_is_connected,
        mode="mongodb_atlas" if _is_connected else "in_memory_fallback",
        database_name=db_name if _is_connected else "local_memory",
        message=_connection_message,
        instructions=instructions_text if not _is_connected else None,
    )


async def create_ticket(ticket_data: TicketCreate) -> TicketResponse:
    """
    Creates a new ITSM ticket with initial audit history log.
    Saves to MongoDB Atlas if connected; otherwise falls back to in-memory store.
    """
    global _next_ticket_sequence
    now_iso = datetime.now(timezone.utc).isoformat()

    initial_event = {
        "timestamp": now_iso,
        "actor": ticket_data.requester or "IT Helpdesk User",
        "action": "Created",
        "note": f"Incident logged with priority {ticket_data.priority.value}",
    }

    if _is_connected and _db is not None:
        # Determine next ticket number based on highest numeric ticket_number in DB
        latest_ticket = await _db.tickets.find_one({}, sort=[("ticket_number", -1)])
        next_seq = 1001
        if latest_ticket and "ticket_number" in latest_ticket:
            try:
                num = int(str(latest_ticket["ticket_number"]).split("-")[-1])
                next_seq = max(next_seq, num + 1)
            except (ValueError, IndexError):
                count = await _db.tickets.count_documents({})
                next_seq = 1001 + count

        ticket_number = f"INC-{next_seq}"

        doc = {
            "ticket_number": ticket_number,
            "title": ticket_data.title.strip(),
            "description": ticket_data.description.strip(),
            "category": ticket_data.category.value,
            "priority": ticket_data.priority.value,
            "status": TicketStatus.OPEN.value,
            "assignee": ticket_data.assignee or "Unassigned",
            "requester": ticket_data.requester or "IT Helpdesk User",
            "created_at": now_iso,
            "updated_at": now_iso,
            "resolution_notes": None,
            "activity_history": [initial_event],
        }

        result = await _db.tickets.insert_one(doc)
        doc["_id"] = result.inserted_id
        return _dict_to_ticket_response(doc)

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
        "assignee": ticket_data.assignee or "Unassigned",
        "requester": ticket_data.requester or "IT Helpdesk User",
        "created_at": now_iso,
        "updated_at": now_iso,
        "resolution_notes": None,
        "activity_history": [initial_event],
    }
    _in_memory_tickets.insert(0, doc)
    return _dict_to_ticket_response(doc)


async def get_all_tickets(
    search: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
) -> List[TicketResponse]:
    """Retrieves tickets with optional search and filter criteria."""
    results: List[TicketResponse] = []

    if _is_connected and _db is not None:
        query: Dict[str, Any] = {}
        if category and category != "ALL":
            query["category"] = category
        if priority and priority != "ALL":
            query["priority"] = priority
        if status and status != "ALL":
            query["status"] = status
        if assignee and assignee != "ALL":
            query["assignee"] = assignee
        if search:
            q = search.strip()
            query["$or"] = [
                {"ticket_number": {"$regex": q, "$options": "i"}},
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
                {"requester": {"$regex": q, "$options": "i"}},
            ]

        cursor = _db.tickets.find(query).sort("created_at", -1)
        async for doc in cursor:
            results.append(_dict_to_ticket_response(doc))
        return results

    # In-memory fallback filtering
    for doc in _in_memory_tickets:
        if search:
            q = search.lower().strip()
            match_id = q in doc["ticket_number"].lower()
            match_title = q in doc["title"].lower()
            match_desc = q in doc.get("description", "").lower()
            match_req = q in doc.get("requester", "").lower()
            if not (match_id or match_title or match_desc or match_req):
                continue

        if category and category != "ALL" and doc["category"] != category:
            continue
        if priority and priority != "ALL" and doc["priority"] != priority:
            continue
        if status and status != "ALL" and doc["status"] != status:
            continue
        if assignee and assignee != "ALL" and doc.get("assignee") != assignee:
            continue

        results.append(_dict_to_ticket_response(doc))

    return results


async def get_ticket_by_id(ticket_id: str) -> Optional[TicketResponse]:
    """Retrieves an incident by its internal ID or ticket_number."""
    ticket_id_clean = ticket_id.strip()

    if _is_connected and _db is not None:
        from bson import ObjectId
        conditions: List[Dict[str, Any]] = [
            {"ticket_number": {"$regex": f"^{ticket_id_clean}$", "$options": "i"}}
        ]
        if ObjectId.is_valid(ticket_id_clean):
            conditions.append({"_id": ObjectId(ticket_id_clean)})
        doc = await _db.tickets.find_one({"$or": conditions})
        return _dict_to_ticket_response(doc) if doc else None

    for doc in _in_memory_tickets:
        if doc["id"] == ticket_id_clean or doc["ticket_number"].upper() == ticket_id_clean.upper():
            return _dict_to_ticket_response(doc)
    return None


async def update_ticket(ticket_id: str, updates: TicketUpdate) -> Optional[TicketResponse]:
    """
    Updates ticket fields and appends an ActivityLogEntry to track the lifecycle.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    target_doc = None
    actor = updates.updated_by or "IT Support Agent"

    if _is_connected and _db is not None:
        from bson import ObjectId
        conditions: List[Dict[str, Any]] = [
            {"ticket_number": {"$regex": f"^{ticket_id.strip()}$", "$options": "i"}}
        ]
        if ObjectId.is_valid(ticket_id.strip()):
            conditions.append({"_id": ObjectId(ticket_id.strip())})
        target_doc = await _db.tickets.find_one({"$or": conditions})
    else:
        for doc in _in_memory_tickets:
            if doc["id"] == ticket_id.strip() or doc["ticket_number"].upper() == ticket_id.strip().upper():
                target_doc = doc
                break

    if not target_doc:
        return None

    activity_events = []
    if updates.status and updates.status.value != target_doc["status"]:
        activity_events.append({
            "timestamp": now_iso,
            "actor": actor,
            "action": "Status Change",
            "note": f"Status changed from {target_doc['status']} to {updates.status.value}",
        })
        target_doc["status"] = updates.status.value

    if updates.assignee and updates.assignee != target_doc.get("assignee"):
        activity_events.append({
            "timestamp": now_iso,
            "actor": actor,
            "action": "Reassigned",
            "note": f"Assigned to {updates.assignee}",
        })
        target_doc["assignee"] = updates.assignee

    if updates.priority and updates.priority.value != target_doc["priority"]:
        activity_events.append({
            "timestamp": now_iso,
            "actor": actor,
            "action": "Priority Update",
            "note": f"Priority updated from {target_doc['priority']} to {updates.priority.value}",
        })
        target_doc["priority"] = updates.priority.value

    if updates.resolution_notes:
        target_doc["resolution_notes"] = updates.resolution_notes.strip()
        activity_events.append({
            "timestamp": now_iso,
            "actor": actor,
            "action": "Resolution Note",
            "note": updates.resolution_notes.strip(),
        })

    if updates.title:
        target_doc["title"] = updates.title.strip()
    if updates.description:
        target_doc["description"] = updates.description.strip()

    target_doc["updated_at"] = now_iso
    if "activity_history" not in target_doc:
        target_doc["activity_history"] = []
    target_doc["activity_history"].extend(activity_events)

    if _is_connected and _db is not None:
        await _db.tickets.replace_one({"_id": target_doc["_id"]}, target_doc)

    return _dict_to_ticket_response(target_doc)


async def get_dashboard_stats() -> DashboardStatsResponse:
    """Calculates operational metrics from all active incident records."""
    tickets = await get_all_tickets()

    by_category = {cat.value: 0 for cat in TicketCategory}
    by_priority = {p.value: 0 for p in TicketPriority}
    by_status = {s.value: 0 for s in TicketStatus}

    open_count = 0
    in_progress_count = 0
    resolved_count = 0
    closed_count = 0
    high_critical_count = 0

    for t in tickets:
        by_category[t.category.value] = by_category.get(t.category.value, 0) + 1
        by_priority[t.priority.value] = by_priority.get(t.priority.value, 0) + 1
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1

        if t.status == TicketStatus.OPEN:
            open_count += 1
        elif t.status == TicketStatus.IN_PROGRESS:
            in_progress_count += 1
        elif t.status == TicketStatus.RESOLVED:
            resolved_count += 1
        elif t.status == TicketStatus.CLOSED:
            closed_count += 1

        if t.priority in (TicketPriority.HIGH, TicketPriority.CRITICAL):
            high_critical_count += 1

    return DashboardStatsResponse(
        total=len(tickets),
        open=open_count,
        in_progress=in_progress_count,
        resolved=resolved_count,
        closed=closed_count,
        high_critical=high_critical_count,
        by_category=by_category,
        by_priority=by_priority,
        by_status=by_status,
    )


async def get_kb_articles(
    search: Optional[str] = None,
    category: Optional[str] = None,
) -> List[KBArticle]:
    """Retrieves searchable Knowledge Base demonstration articles."""
    results: List[KBArticle] = []

    if _is_connected and _db is not None:
        query: Dict[str, Any] = {}
        if category and category != "ALL":
            query["category"] = {"$regex": f"^{category}$", "$options": "i"}
        if search:
            q = search.strip()
            query["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"excerpt": {"$regex": q, "$options": "i"}},
                {"content": {"$regex": q, "$options": "i"}},
                {"tags": {"$regex": q, "$options": "i"}},
            ]
        cursor = _db.knowledge_base.find(query).sort("id", 1)
        async for doc in cursor:
            results.append(KBArticle(**{k: v for k, v in doc.items() if k != "_id"}))
        return results

    # In-memory fallback
    for art in _DEMO_KB_ARTICLES:
        if category and category != "ALL" and art["category"].lower() != category.lower():
            continue
        if search:
            q = search.lower().strip()
            match_title = q in art["title"].lower()
            match_excerpt = q in art["excerpt"].lower()
            match_content = q in art["content"].lower()
            match_tag = any(q in tag.lower() for tag in art.get("tags", []))
            if not (match_title or match_excerpt or match_content or match_tag):
                continue
        results.append(KBArticle(**art))
    return results
