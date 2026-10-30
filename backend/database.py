import os
import re
import time
import asyncio
import logging
from pathlib import Path
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
    UserRole,
    UserProfile,
    RequestCategory,
    RequestStatus,
    CatalogItem,
    ServiceRequestCreate,
    ServiceRequestStatusUpdate,
    ServiceRequestResponse,
    WorkSession,
    TimerActionRequest,
    TicketTimerStatusResponse,
    KBArticleCreate,
    KBArticleUpdate,
)

# Load environment variables from backend/.env – explicit path so this works
# regardless of which directory the process was launched from.
_ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=False)

# Logger configuration
logger = logging.getLogger("helpwise.database")

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DATABASE_NAME = os.getenv("DATABASE_NAME", "helpwise_ai").strip()

# Internal state tracking
_mongo_client = None
_db = None
_is_connected = False
# Set to True when MONGODB_URI is configured but connection failed or dropped.
_atlas_configured_but_unreachable = False
_connection_message = "In-memory development fallback active. Configure MONGODB_URI in backend/.env for persistent Atlas storage."
_last_reconnect_attempt = 0.0
_RECONNECT_INTERVAL_SECONDS = 4.0
_auto_reconnect_enabled = True


class DatabaseUnavailableError(RuntimeError):
    """Raised when an operation is attempted but the configured Atlas database is unreachable."""
    pass


def _is_atlas_configured() -> bool:
    load_dotenv(dotenv_path=_ENV_FILE, override=False)
    uri = os.getenv("MONGODB_URI", "").strip()
    return bool(uri and not uri.startswith("your_") and "<username>" not in uri)


def _mark_atlas_unreachable(exc: Optional[Exception] = None) -> None:
    global _is_connected, _atlas_configured_but_unreachable, _connection_message
    _is_connected = False
    _atlas_configured_but_unreachable = True
    if exc:
        sanitized = _sanitize_error_message(exc)
        _connection_message = (
            f"MongoDB Atlas connection lost: {sanitized}. "
            "Please verify your current IP address is whitelisted in MongoDB Atlas Network Access."
        )
        logger.warning(f"MongoDB Atlas connection lost: {sanitized}")


def _use_mongo() -> bool:
    return bool(_is_connected and _db is not None)


def _require_atlas_for_read() -> None:
    if _atlas_configured_but_unreachable:
        raise DatabaseUnavailableError(
            "MongoDB Atlas is configured but currently unreachable. "
            "Cannot retrieve records from the database. "
            "Please verify your current IP address is whitelisted in MongoDB Atlas Network Access."
        )


def _require_atlas_for_write() -> None:
    if _atlas_configured_but_unreachable:
        raise DatabaseUnavailableError(
            "MongoDB Atlas is configured but currently unreachable. "
            "Cannot persist this change. "
            "Please verify your current IP address is whitelisted in MongoDB Atlas Network Access."
        )


async def _try_auto_reconnect_if_needed() -> bool:
    global _last_reconnect_attempt
    if not _auto_reconnect_enabled or not _atlas_configured_but_unreachable:
        return _is_connected

    now = time.monotonic()
    if now - _last_reconnect_attempt < _RECONNECT_INTERVAL_SECONDS:
        return False

    _last_reconnect_attempt = now
    logger.info("Attempting automatic reconnection to MongoDB Atlas...")
    try:
        return await init_db()
    except Exception as exc:
        logger.warning(f"Auto-reconnect attempt failed: {_sanitize_error_message(exc)}")
        return False


async def _insert_unique(
    collection,
    doc: Dict[str, Any],
    id_field: str,
    prefix: str,
    next_seq_fn,
    max_attempts: int = 8,
) -> Dict[str, Any]:
    """Insert doc with a freshly allocated INC-/REQ- number; retry on duplicate key."""
    from pymongo.errors import DuplicateKeyError

    last_error: Optional[Exception] = None
    for _ in range(max_attempts):
        seq = await next_seq_fn()
        doc[id_field] = f"{prefix}-{seq}"
        doc.pop("_id", None)
        try:
            result = await collection.insert_one(doc)
            doc["_id"] = result.inserted_id
            return doc
        except DuplicateKeyError as exc:
            last_error = exc
            continue
    raise DatabaseUnavailableError(
        f"Could not allocate a unique {id_field} after {max_attempts} attempts."
    ) from last_error

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

USER_PERSONAS: List[UserProfile] = [
    UserProfile(
        username="alex.morgan",
        name="Alex Morgan",
        email="alex.morgan@company.internal",
        role=UserRole.EMPLOYEE,
        department="Engineering",
        avatar="👨‍💻",
    ),
    UserProfile(
        username="sarah.chen",
        name="Sarah Chen",
        email="sarah.chen@helpwise.ai",
        role=UserRole.AGENT,
        department="IT Operations",
        avatar="👩‍🔧",
    ),
    UserProfile(
        username="marcus.vance",
        name="Marcus Vance",
        email="marcus.vance@helpwise.ai",
        role=UserRole.ADMIN,
        department="IT Management",
        avatar="👨‍💼",
    ),
]

CATALOG_ITEMS: List[CatalogItem] = [
    CatalogItem(
        id="cat-101",
        name="Visual Studio Code Enterprise",
        category=RequestCategory.SOFTWARE,
        description="Standard development editor with pre-configured corporate plugins, Copilot access, and linting rules.",
        requires_approval=False,
        estimated_delivery="15 minutes (Automated)",
        icon="💻",
    ),
    CatalogItem(
        id="cat-102",
        name="JetBrains All Products Pack License",
        category=RequestCategory.SOFTWARE,
        description="Commercial license for IntelliJ IDEA Ultimate, PyCharm Professional, WebStorm, and GoLand.",
        requires_approval=True,
        estimated_delivery="1-2 business days",
        icon="⚡",
    ),
    CatalogItem(
        id="cat-103",
        name="Docker Desktop Commercial License",
        category=RequestCategory.SOFTWARE,
        description="Container virtualization engine with Kubernetes support for local development.",
        requires_approval=True,
        estimated_delivery="4 hours",
        icon="🐳",
    ),
    CatalogItem(
        id="cat-104",
        name="Postman Enterprise Workspace Access",
        category=RequestCategory.SOFTWARE,
        description="API collaboration and testing platform with shared corporate mock servers and environments.",
        requires_approval=False,
        estimated_delivery="30 minutes",
        icon="🚀",
    ),
    CatalogItem(
        id="cat-105",
        name="AWS / GCP Cloud Sandbox Environment",
        category=RequestCategory.ACCESS,
        description="Isolated development cloud project with pre-budgeted resources ($250/month limit).",
        requires_approval=True,
        estimated_delivery="1 business day",
        icon="☁️",
    ),
    CatalogItem(
        id="cat-106",
        name="Corporate VPN Remote Access Profile",
        category=RequestCategory.NETWORK,
        description="802.1X and Cisco AnyConnect certificate configuration for secure remote network tunneling.",
        requires_approval=False,
        estimated_delivery="Instant",
        icon="🔒",
    ),
    CatalogItem(
        id="cat-107",
        name="Secondary 27-inch 4K Monitor",
        category=RequestCategory.HARDWARE,
        description="Dell UltraSharp USB-C Hub Monitor (4K IPS) with display cables and desk mount.",
        requires_approval=True,
        estimated_delivery="3-5 business days",
        icon="🖥️",
    ),
    CatalogItem(
        id="cat-108",
        name="YubiKey 5 FIDO2 Hardware Security Key",
        category=RequestCategory.HARDWARE,
        description="Physical USB-C / NFC authentication key for passwordless multi-factor authentication.",
        requires_approval=False,
        estimated_delivery="1 business day",
        icon="🔑",
    ),
]

_in_memory_service_requests: List[Dict[str, Any]] = [
    {
        "id": "req_5001",
        "request_number": "REQ-5001",
        "catalog_item_id": "cat-103",
        "item_name": "Docker Desktop Commercial License",
        "category": RequestCategory.SOFTWARE.value,
        "justification": "Required for building and testing microservice containers in the local Helpdesk environment.",
        "additional_info": "Windows WSL2 environment",
        "requester": "Alex Morgan",
        "department": "Engineering",
        "status": RequestStatus.APPROVED.value,
        "requires_approval": True,
        "approver": "Marcus Vance",
        "approval_notes": "Approved for Engineering team members.",
        "created_at": "2026-10-19T09:30:00.000000Z",
        "updated_at": "2026-10-19T11:00:00.000000Z",
        "activity_history": [
            {"timestamp": "2026-10-19T09:30:00.000000Z", "actor": "Alex Morgan", "action": "Submitted", "note": "Service request submitted for approval."},
            {"timestamp": "2026-10-19T11:00:00.000000Z", "actor": "Marcus Vance", "action": "Approved", "note": "Approved for Engineering team members."},
        ],
    },
    {
        "id": "req_5002",
        "request_number": "REQ-5002",
        "catalog_item_id": "cat-105",
        "item_name": "AWS / GCP Cloud Sandbox Environment",
        "category": RequestCategory.ACCESS.value,
        "justification": "Need sandbox environment to test MongoDB Atlas VPC peering and vector store migration.",
        "additional_info": "GCP Project us-central1",
        "requester": "Alex Morgan",
        "department": "Engineering",
        "status": RequestStatus.PENDING_APPROVAL.value,
        "requires_approval": True,
        "approver": None,
        "approval_notes": None,
        "created_at": "2026-10-21T08:15:00.000000Z",
        "updated_at": "2026-10-21T08:15:00.000000Z",
        "activity_history": [
            {"timestamp": "2026-10-21T08:15:00.000000Z", "actor": "Alex Morgan", "action": "Submitted", "note": "Service request submitted for approval."},
        ],
    },
    {
        "id": "req_5003",
        "request_number": "REQ-5003",
        "catalog_item_id": "cat-107",
        "item_name": "Secondary 27-inch 4K Monitor",
        "category": RequestCategory.HARDWARE.value,
        "justification": "Ergonomic hardware upgrade for multi-window ticket dispatch and monitoring.",
        "additional_info": "Desk 4B, Building 2",
        "requester": "Sarah Chen",
        "department": "IT Operations",
        "status": RequestStatus.FULFILLED.value,
        "requires_approval": True,
        "approver": "Marcus Vance",
        "approval_notes": "Delivered and installed by Facilities IT.",
        "created_at": "2026-10-15T10:00:00.000000Z",
        "updated_at": "2026-10-17T14:30:00.000000Z",
        "activity_history": [
            {"timestamp": "2026-10-15T10:00:00.000000Z", "actor": "Sarah Chen", "action": "Submitted", "note": "Request submitted."},
            {"timestamp": "2026-10-16T09:00:00.000000Z", "actor": "Marcus Vance", "action": "Approved", "note": "Approved."},
            {"timestamp": "2026-10-17T14:30:00.000000Z", "actor": "Facilities IT", "action": "Fulfilled", "note": "Equipment delivered."},
        ],
    },
]

_in_memory_work_sessions: List[Dict[str, Any]] = [
    {
        "id": "sess_2001",
        "ticket_id": "mem_1001",
        "ticket_number": "INC-1001",
        "agent": "Sarah Chen",
        "start_time": "2026-10-18T13:00:00.000000Z",
        "stop_time": "2026-10-18T13:45:00.000000Z",
        "duration_seconds": 2700,
        "is_active": False,
        "note": "Diagnosed TLS certificate handshake error and root CA installation.",
    },
    {
        "id": "sess_2002",
        "ticket_id": "mem_1001",
        "ticket_number": "INC-1001",
        "agent": "Sarah Chen",
        "start_time": "2026-10-18T14:00:00.000000Z",
        "stop_time": "2026-10-18T14:30:00.000000Z",
        "duration_seconds": 1800,
        "is_active": False,
        "note": "Verified AnyConnect connection from external IP and closed ticket.",
    },
]

_next_request_sequence = 5004
_next_session_sequence = 2003



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
        # 3. Indexes on service_requests
        await _db.service_requests.create_index("request_number", unique=True)
        await _db.service_requests.create_index("requester")
        # 4. Indexes on work_sessions
        await _db.work_sessions.create_index("ticket_id")
        await _db.work_sessions.create_index("agent")

        # 5. Seed demo tickets if empty
        ticket_count = await _db.tickets.count_documents({})
        if ticket_count == 0:
            for item in _in_memory_tickets:
                doc = dict(item)
                # Remove in-memory "id" key so Mongo generates native _id
                doc.pop("id", None)
                await _db.tickets.insert_one(doc)
            logger.info("Successfully seeded demo ITSM tickets into MongoDB Atlas")

        # 6. Seed demo Knowledge Base articles if empty
        kb_count = await _db.knowledge_base.count_documents({})
        if kb_count == 0:
            for article in _DEMO_KB_ARTICLES:
                doc = dict(article)
                await _db.knowledge_base.insert_one(doc)
            logger.info("Successfully seeded demo KB articles into MongoDB Atlas")

        # 7. Seed demo service requests if empty
        sr_count = await _db.service_requests.count_documents({})
        if sr_count == 0:
            for sr in _in_memory_service_requests:
                doc = dict(sr)
                doc.pop("id", None)
                await _db.service_requests.insert_one(doc)
            logger.info("Successfully seeded demo service requests into MongoDB Atlas")

        # 8. Seed demo work sessions if empty
        ws_count = await _db.work_sessions.count_documents({})
        if ws_count == 0:
            for ws in _in_memory_work_sessions:
                doc = dict(ws)
                doc.pop("id", None)
                await _db.work_sessions.insert_one(doc)
            logger.info("Successfully seeded demo work sessions into MongoDB Atlas")

    except Exception as exc:
        sanitized = _sanitize_error_message(exc)
        logger.warning(f"Note during index/seed check: {sanitized}")


async def init_db() -> bool:
    """
    Attempts to connect to MongoDB Atlas if MONGODB_URI is provided.
    If not provided or placeholder → unconfigured in-memory fallback (safe for local dev).
    If URI is configured but connection fails → mark _atlas_configured_but_unreachable=True;
      write operations will raise DatabaseUnavailableError so callers surface a 503 error.
    Never exposes credentials or secrets in logs, messages, or exceptions.
    """
    global _mongo_client, _db, _is_connected, _connection_message, _atlas_configured_but_unreachable

    # Re-read environment variables in case .env was modified
    load_dotenv(dotenv_path=_ENV_FILE, override=True)
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
        _atlas_configured_but_unreachable = False
        _mongo_client = None
        _db = None
        _connection_message = (
            "MONGODB_URI is not configured in backend/.env. Running on in-memory storage fallback."
        )
        return False

    # URI is explicitly configured — attempt connection.
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        # Cleanly close previous client if re-initializing
        if _mongo_client is not None:
            try:
                _mongo_client.close()
            except Exception:
                pass
            _mongo_client = None

        client = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            maxIdleTimeMS=45000,
            maxPoolSize=20,
            minPoolSize=1,
            retryWrites=True,
            retryReads=True,
        )
        # Retry ping once: Atlas SRV DNS lookups can occasionally fail on the first attempt.
        ping_error: Optional[Exception] = None
        for _attempt in range(2):
            try:
                await client.admin.command("ping")
                ping_error = None
                break
            except Exception as ping_exc:
                ping_error = ping_exc
        if ping_error is not None:
            try:
                client.close()
            except Exception:
                pass
            raise ping_error

        _mongo_client = client
        _db = _mongo_client[db_name]
        _is_connected = True
        _atlas_configured_but_unreachable = False
        _connection_message = f"Successfully connected to MongoDB Atlas database: '{db_name}'"

        # Ensure indexes and initial demonstration data are present
        await _ensure_indexes_and_seed()
        return True

    except Exception as exc:
        _is_connected = False
        _atlas_configured_but_unreachable = True   # URI was configured but unreachable
        _mongo_client = None
        _db = None
        sanitized_err = _sanitize_error_message(exc)
        _connection_message = (
            f"MongoDB Atlas is configured but unreachable: {sanitized_err}. "
            "Write operations are DISABLED to prevent silent data loss. "
            "Please verify your IP is whitelisted in MongoDB Atlas Network Access and retry."
        )
        logger.error(f"MongoDB Atlas configured but connection failed: {sanitized_err}")
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


async def get_storage_status(check_live: bool = True) -> StorageStatusResponse:
    """Returns metadata about the active storage layer, verifying live connectivity if connected."""
    global _mongo_client, _db, _is_connected, _connection_message, _atlas_configured_but_unreachable

    # 1. If currently marked unreachable, attempt auto-reconnecting if enough time has passed
    if _atlas_configured_but_unreachable:
        await _try_auto_reconnect_if_needed()

    # 2. If marked connected and live check requested, verify socket with a quick ping
    elif _is_connected and _mongo_client is not None and check_live:
        try:
            await asyncio.wait_for(_mongo_client.admin.command("ping"), timeout=2.5)
        except Exception as exc:
            _mark_atlas_unreachable(exc)

    db_name = os.getenv("DATABASE_NAME", "helpwise_ai").strip()
    instructions_text = (
        "To connect MongoDB Atlas:\n"
        "1. Open MongoDB Atlas (cloud.mongodb.com) and navigate to your cluster 'HelpWiseCluster'.\n"
        "2. Ensure your current IP address is added in Network Access.\n"
        "3. Copy your connection string and add it to backend/.env: MONGODB_URI=...\n"
        "4. The system will automatically reconnect once your IP is active."
    )
    if _is_connected:
        mode = "mongodb_atlas"
        db_name_out = db_name
    elif _atlas_configured_but_unreachable:
        mode = "atlas_unreachable"
        db_name_out = db_name  # URI was pointing here, just not reachable
    else:
        mode = "in_memory_fallback"
        db_name_out = "local_memory"
    return StorageStatusResponse(
        connected=_is_connected,
        mode=mode,
        database_name=db_name_out,
        message=_connection_message,
        instructions=instructions_text if not _is_connected else None,
    )


def _next_safe_ticket_sequence() -> int:
    """
    Calculates the next safe ticket sequence number by scanning ALL known INC-NNNN
    identifiers across in-memory records, extracting the numeric suffix, and returning
    max + 1.  This prevents collisions even after restarts or ID gaps.
    """
    max_num = 1000  # floor so first ID is INC-1001
    pattern = re.compile(r"INC-(\d+)$", re.IGNORECASE)
    for doc in _in_memory_tickets:
        m = pattern.match(str(doc.get("ticket_number", "")))
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num + 1


async def _next_safe_ticket_sequence_mongo() -> int:
    """
    Calculates the next safe ticket sequence number by scanning all ticket_number
    values in MongoDB and extracting the highest numeric suffix.
    Uses a full collection scan (capped at 1000 docs) to avoid alphabetical sort bugs.
    """
    max_num = 1000
    pattern = re.compile(r"INC-(\d+)$", re.IGNORECASE)
    cursor = _db.tickets.find({}, {"ticket_number": 1, "_id": 0}).limit(5000)
    async for doc in cursor:
        m = pattern.match(str(doc.get("ticket_number", "")))
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num + 1


async def create_ticket(ticket_data: TicketCreate) -> TicketResponse:
    """
    Creates a new ITSM ticket with initial audit history log.
    Saves to MongoDB Atlas if connected.
    Raises DatabaseUnavailableError when Atlas is configured but unreachable.
    Falls back to in-memory ONLY when Atlas URI is not configured (local dev mode).
    """
    global _next_ticket_sequence
    now_iso = datetime.now(timezone.utc).isoformat()

    await _try_auto_reconnect_if_needed()
    _require_atlas_for_write()

    initial_event = {
        "timestamp": now_iso,
        "actor": ticket_data.requester or "IT Helpdesk User",
        "action": "Created",
        "note": f"Incident logged with priority {ticket_data.priority.value}",
    }

    if _use_mongo():
        try:
            doc = {
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
            doc = await _insert_unique(
                _db.tickets,
                doc,
                id_field="ticket_number",
                prefix="INC",
                next_seq_fn=_next_safe_ticket_sequence_mongo,
            )
            return _dict_to_ticket_response(doc)
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to create incident in MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

    # In-memory storage fallback (only when Atlas is NOT configured)
    next_seq = _next_safe_ticket_sequence()
    _next_ticket_sequence = next_seq + 1  # keep global counter in sync
    ticket_number = f"INC-{next_seq}"

    doc = {
        "id": f"mem_{next_seq}",
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
    requester: Optional[str] = None,
) -> List[TicketResponse]:
    """Retrieves tickets with optional search and filter criteria."""
    results: List[TicketResponse] = []

    await _try_auto_reconnect_if_needed()

    if _use_mongo():
        try:
            query: Dict[str, Any] = {}
            if category and category != "ALL":
                query["category"] = category
            if priority and priority != "ALL":
                query["priority"] = priority
            if status and status != "ALL":
                query["status"] = status
            if assignee and assignee != "ALL":
                query["assignee"] = assignee
            if requester and requester != "ALL":
                query["requester"] = {"$regex": f"^{re.escape(requester)}$", "$options": "i"}
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
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to query incidents from MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

    _require_atlas_for_read()

    # In-memory fallback filtering (only when Atlas URI is not configured)
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
        if requester and requester != "ALL" and doc.get("requester", "").lower() != requester.lower():
            continue

        results.append(_dict_to_ticket_response(doc))

    return results


async def get_ticket_by_id(ticket_id: str) -> Optional[TicketResponse]:
    """Retrieves an incident by its internal ID or ticket_number."""
    ticket_id_clean = ticket_id.strip()

    await _try_auto_reconnect_if_needed()

    if _use_mongo():
        try:
            from bson import ObjectId
            conditions: List[Dict[str, Any]] = [
                {"ticket_number": {"$regex": f"^{ticket_id_clean}$", "$options": "i"}}
            ]
            if ObjectId.is_valid(ticket_id_clean):
                conditions.append({"_id": ObjectId(ticket_id_clean)})
            doc = await _db.tickets.find_one({"$or": conditions})
            return _dict_to_ticket_response(doc) if doc else None
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to retrieve incident from MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

    _require_atlas_for_read()

    for doc in _in_memory_tickets:
        if doc["id"] == ticket_id_clean or doc["ticket_number"].upper() == ticket_id_clean.upper():
            return _dict_to_ticket_response(doc)
    return None


async def update_ticket(ticket_id: str, updates: TicketUpdate) -> Optional[TicketResponse]:
    """
    Updates ticket fields and appends an ActivityLogEntry to track the lifecycle.
    """
    await _try_auto_reconnect_if_needed()
    _require_atlas_for_write()
    now_iso = datetime.now(timezone.utc).isoformat()
    target_doc = None
    actor = updates.updated_by or "IT Support Agent"

    if _use_mongo():
        try:
            from bson import ObjectId
            conditions: List[Dict[str, Any]] = [
                {"ticket_number": {"$regex": f"^{ticket_id.strip()}$", "$options": "i"}}
            ]
            if ObjectId.is_valid(ticket_id.strip()):
                conditions.append({"_id": ObjectId(ticket_id.strip())})
            target_doc = await _db.tickets.find_one({"$or": conditions})
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to query incident to update in MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc
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
        try:
            await _db.tickets.replace_one({"_id": target_doc["_id"]}, target_doc)
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to persist incident update in MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

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

    await _try_auto_reconnect_if_needed()

    if _is_connected and _db is not None:
        try:
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
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to query knowledge base from MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

    _require_atlas_for_read()

    # In-memory fallback (only when Atlas is not configured)
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


# ── Service Requests & Catalogue Operations ──────────────────────────────────

def _dict_to_service_request(doc: Dict[str, Any]) -> ServiceRequestResponse:
    justification_val = doc.get("justification") or doc.get("business_justification") or ""
    additional_val = doc.get("additional_info") or doc.get("additional_details")
    return ServiceRequestResponse(
        id=str(doc.get("_id", doc.get("id"))),
        request_number=doc["request_number"],
        catalog_item_id=doc["catalog_item_id"],
        item_name=doc["item_name"],
        category=doc["category"],
        justification=justification_val,
        business_justification=justification_val,
        additional_info=additional_val,
        additional_details=additional_val,
        requester=doc["requester"],
        department=doc.get("department", "Engineering"),
        status=RequestStatus(doc["status"]),
        requires_approval=doc.get("requires_approval", True),
        approver=doc.get("approver"),
        approval_notes=doc.get("approval_notes"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        activity_history=[
            ActivityLogEntry(**entry)
            for entry in doc.get("activity_history", [])
        ],
    )


def _dict_to_work_session(doc: Dict[str, Any]) -> WorkSession:
    dur_sec = int(doc.get("duration_seconds", 0))
    return WorkSession(
        id=str(doc.get("_id", doc.get("id"))),
        ticket_id=str(doc["ticket_id"]),
        ticket_number=doc["ticket_number"],
        agent=doc["agent"],
        start_time=doc["start_time"],
        stop_time=doc.get("stop_time"),
        duration_seconds=dur_sec,
        duration_minutes=max(0, dur_sec // 60),
        is_active=bool(doc.get("is_active", False)),
        note=doc.get("note"),
    )


async def get_catalog_items() -> List[CatalogItem]:
    """Returns the available service catalogue items."""
    return list(CATALOG_ITEMS)


async def get_catalog_item_by_id(item_id: str) -> Optional[CatalogItem]:
    for item in CATALOG_ITEMS:
        if item.id == item_id:
            return item
    return None


def _next_safe_request_sequence() -> int:
    """
    Calculates the next safe service-request sequence number by scanning ALL known REQ-NNNN
    identifiers across in-memory records. Uses numeric max + 1, never alphabetical sort.
    """
    max_num = 5000  # floor so first ID is REQ-5001
    pattern = re.compile(r"REQ-(\d+)$", re.IGNORECASE)
    for doc in _in_memory_service_requests:
        m = pattern.match(str(doc.get("request_number", "")))
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num + 1


async def _next_safe_request_sequence_mongo() -> int:
    """
    Calculates the next safe service-request sequence number by scanning all request_number
    values in MongoDB and extracting the highest numeric suffix.
    Uses a full collection scan to avoid alphabetical sort bugs ("REQ-599" > "REQ-5001").
    """
    max_num = 5000
    pattern = re.compile(r"REQ-(\d+)$", re.IGNORECASE)
    cursor = _db.service_requests.find({}, {"request_number": 1, "_id": 0}).limit(5000)
    async for doc in cursor:
        m = pattern.match(str(doc.get("request_number", "")))
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num + 1


async def create_service_request(
    payload: ServiceRequestCreate,
    actor: Optional[str] = None
) -> ServiceRequestResponse:
    """
    Creates and persists a new Service Request.
    Raises DatabaseUnavailableError when Atlas is configured but unreachable.
    Falls back to in-memory ONLY when Atlas URI is not configured (local dev mode).
    """
    global _next_request_sequence
    now_iso = datetime.now(timezone.utc).isoformat()

    await _try_auto_reconnect_if_needed()
    _require_atlas_for_write()

    catalog_item = await get_catalog_item_by_id(payload.catalog_item_id)
    requires_approval = catalog_item.requires_approval if catalog_item else True
    initial_status = RequestStatus.PENDING_APPROVAL if requires_approval else RequestStatus.APPROVED

    initial_event = {
        "timestamp": now_iso,
        "actor": actor or payload.requester,
        "action": "Submitted",
        "note": f"Service request submitted for {payload.item_name}. {'Approval required.' if requires_approval else 'Pre-approved automated item.'}",
    }

    if _use_mongo():
        try:
            justification_text = payload.get_justification()
            additional_text = (payload.additional_details or payload.additional_info or "").strip() or None
            doc = {
                "catalog_item_id": payload.catalog_item_id,
                "item_name": payload.item_name,
                "category": payload.category.value if hasattr(payload.category, "value") else str(payload.category),
                "justification": justification_text,
                "additional_info": additional_text,
                "requester": payload.requester,
                "department": payload.department or "Engineering",
                "status": initial_status.value,
                "requires_approval": requires_approval,
                "approver": None,
                "approval_notes": None,
                "created_at": now_iso,
                "updated_at": now_iso,
                "activity_history": [initial_event],
            }
            doc = await _insert_unique(
                _db.service_requests,
                doc,
                id_field="request_number",
                prefix="REQ",
                next_seq_fn=_next_safe_request_sequence_mongo,
            )
            return _dict_to_service_request(doc)
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to create service request in MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

    # In-memory fallback (only when Atlas is NOT configured)
    next_seq = _next_safe_request_sequence()
    _next_request_sequence = next_seq + 1  # keep global counter in sync
    request_number = f"REQ-{next_seq}"
    justification_text = payload.get_justification()
    additional_text = (payload.additional_details or payload.additional_info or "").strip() or None
    doc = {
        "id": f"mem_req_{next_seq}",
        "request_number": request_number,
        "catalog_item_id": payload.catalog_item_id,
        "item_name": payload.item_name,
        "category": payload.category.value if hasattr(payload.category, "value") else str(payload.category),
        "justification": justification_text,
        "additional_info": additional_text,
        "requester": payload.requester,
        "department": payload.department or "Engineering",
        "status": initial_status.value,
        "requires_approval": requires_approval,
        "approver": None,
        "approval_notes": None,
        "created_at": now_iso,
        "updated_at": now_iso,
        "activity_history": [initial_event],
    }
    _in_memory_service_requests.insert(0, doc)
    return _dict_to_service_request(doc)


async def get_service_requests(
    requester: Optional[str] = None,
    status: Optional[str] = None,
) -> List[ServiceRequestResponse]:
    """Retrieves service requests with optional requester or status filter."""
    results: List[ServiceRequestResponse] = []

    await _try_auto_reconnect_if_needed()

    if _use_mongo():
        try:
            query: Dict[str, Any] = {}
            if requester and requester != "ALL":
                query["requester"] = {"$regex": f"^{re.escape(requester)}$", "$options": "i"}
            if status and status != "ALL":
                query["status"] = status

            cursor = _db.service_requests.find(query).sort("created_at", -1)
            async for doc in cursor:
                results.append(_dict_to_service_request(doc))
            return results
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to query service requests from MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

    _require_atlas_for_read()

    # In-memory fallback (only when Atlas URI is not configured)
    for doc in _in_memory_service_requests:
        if requester and requester != "ALL" and doc["requester"].lower() != requester.lower():
            continue
        if status and status != "ALL" and doc["status"] != status:
            continue
        results.append(_dict_to_service_request(doc))
    return results


async def get_service_request_by_id(req_id: str) -> Optional[ServiceRequestResponse]:
    clean_id = req_id.strip()

    await _try_auto_reconnect_if_needed()

    if _use_mongo():
        try:
            from bson import ObjectId
            query = {"request_number": clean_id}
            if ObjectId.is_valid(clean_id):
                query = {"$or": [{"_id": ObjectId(clean_id)}, {"request_number": clean_id}]}
            doc = await _db.service_requests.find_one(query)
            return _dict_to_service_request(doc) if doc else None
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to query service request from MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

    _require_atlas_for_read()

    for doc in _in_memory_service_requests:
        if doc.get("id") == clean_id or doc.get("request_number") == clean_id:
            return _dict_to_service_request(doc)
    return None


async def update_service_request_status(
    req_id: str,
    new_status: RequestStatus,
    notes: Optional[str] = None,
    actor: Optional[str] = None,
) -> Optional[ServiceRequestResponse]:
    """Updates the status of a service request (e.g. Approved, Fulfilled, Rejected)."""
    await _try_auto_reconnect_if_needed()
    _require_atlas_for_write()
    now_iso = datetime.now(timezone.utc).isoformat()
    action_name = "Status Change"
    if new_status == RequestStatus.APPROVED:
        action_name = "Approved"
    elif new_status == RequestStatus.REJECTED:
        action_name = "Rejected"
    elif new_status == RequestStatus.FULFILLED:
        action_name = "Fulfilled"
    elif new_status == RequestStatus.CANCELLED:
        action_name = "Cancelled"

    event = {
        "timestamp": now_iso,
        "actor": actor or "Approver",
        "action": action_name,
        "note": notes or f"Request marked as {new_status.value}",
    }

    if _is_connected and _db is not None:
        try:
            from bson import ObjectId
            query = {"request_number": req_id}
            if ObjectId.is_valid(req_id):
                query = {"$or": [{"_id": ObjectId(req_id)}, {"request_number": req_id}]}

            update_fields: Dict[str, Any] = {
                "status": new_status.value,
                "updated_at": now_iso,
            }
            if new_status in (RequestStatus.APPROVED, RequestStatus.REJECTED):
                update_fields["approver"] = actor or "Approver"
                update_fields["approval_notes"] = notes

            await _db.service_requests.update_one(
                query,
                {
                    "$set": update_fields,
                    "$push": {"activity_history": event},
                }
            )
            updated_doc = await _db.service_requests.find_one(query)
            return _dict_to_service_request(updated_doc) if updated_doc else None
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to update service request in MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

    # In-memory fallback
    for doc in _in_memory_service_requests:
        if doc.get("id") == req_id or doc.get("request_number") == req_id:
            doc["status"] = new_status.value
            doc["updated_at"] = now_iso
            if new_status in (RequestStatus.APPROVED, RequestStatus.REJECTED):
                doc["approver"] = actor or "Approver"
                doc["approval_notes"] = notes
            doc.setdefault("activity_history", []).append(event)
            return _dict_to_service_request(doc)
    return None


# ── Work Timers & Ticket Timeline ────────────────────────────────────────────

async def start_work_timer(
    ticket_id: str,
    agent: str,
    note: Optional[str] = None
) -> WorkSession:
    """
    Starts an active work timer for an agent on a ticket.
    Enforces strictly: ONE active work timer per agent at a time.
    """
    global _next_session_sequence
    now_iso = datetime.now(timezone.utc).isoformat()

    _require_atlas_for_write()

    # 1. Check for any existing active session for this agent
    if _is_connected and _db is not None:
        existing = await _db.work_sessions.find_one({"agent": agent, "is_active": True})
        if existing:
            raise ValueError(
                f"Agent '{agent}' already has an active work timer on ticket '{existing['ticket_number']}'. "
                "Stop the active timer before starting a new one."
            )
        # Fetch ticket details
        ticket = await get_ticket_by_id(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket '{ticket_id}' not found.")

        doc = {
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "agent": agent,
            "start_time": now_iso,
            "stop_time": None,
            "duration_seconds": 0,
            "is_active": True,
            "note": note or f"Agent {agent} started work session",
        }
        res = await _db.work_sessions.insert_one(doc)
        doc["_id"] = res.inserted_id

        # Update ticket status to In Progress if currently Open
        if ticket.status == TicketStatus.OPEN:
            await update_ticket(ticket.id, TicketUpdate(status=TicketStatus.IN_PROGRESS))

        return _dict_to_work_session(doc)

    # In-memory fallback
    for ws in _in_memory_work_sessions:
        if ws.get("agent") == agent and ws.get("is_active"):
            raise ValueError(
                f"Agent '{agent}' already has an active work timer on ticket '{ws.get('ticket_number')}'. "
                "Stop the active timer before starting a new one."
            )

    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        raise ValueError(f"Ticket '{ticket_id}' not found.")

    doc = {
        "id": f"sess_{_next_session_sequence}",
        "ticket_id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "agent": agent,
        "start_time": now_iso,
        "stop_time": None,
        "duration_seconds": 0,
        "is_active": True,
        "note": note or f"Agent {agent} started work session",
    }
    _next_session_sequence += 1
    _in_memory_work_sessions.insert(0, doc)

    if ticket.status == TicketStatus.OPEN:
        await update_ticket(ticket.id, TicketUpdate(status=TicketStatus.IN_PROGRESS))

    return _dict_to_work_session(doc)


async def stop_work_timer(
    ticket_id: str,
    agent: str,
    note: Optional[str] = None
) -> WorkSession:
    """Stops an active work timer and computes session duration."""
    _require_atlas_for_write()
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        raise ValueError(f"Ticket '{ticket_id}' not found.")

    if _is_connected and _db is not None:
        session_doc = await _db.work_sessions.find_one({
            "agent": agent,
            "ticket_number": ticket.ticket_number,
            "is_active": True,
        })
        if not session_doc:
            # Check by internal ticket_id as fallback
            session_doc = await _db.work_sessions.find_one({
                "agent": agent,
                "ticket_id": ticket.id,
                "is_active": True,
            })
        if not session_doc:
            raise ValueError(f"No active work session found for agent '{agent}' on ticket '{ticket.ticket_number}'.")

        try:
            start_dt = datetime.fromisoformat(session_doc["start_time"].replace("Z", "+00:00"))
            duration = max(1, int((now_dt - start_dt).total_seconds()))
        except Exception:
            duration = 60

        await _db.work_sessions.update_one(
            {"_id": session_doc["_id"]},
            {
                "$set": {
                    "stop_time": now_iso,
                    "duration_seconds": duration,
                    "is_active": False,
                    "note": note or session_doc.get("note"),
                }
            }
        )

        # Log session event into ticket audit history
        duration_fmt = f"{duration // 60}m {duration % 60}s"
        event = {
            "timestamp": now_iso,
            "actor": agent,
            "action": "Work Session",
            "note": f"Completed work session ({duration_fmt}). {note or ''}".strip(),
        }
        await _db.tickets.update_one(
            {"ticket_number": ticket.ticket_number},
            {"$push": {"activity_history": event}}
        )

        updated_session = await _db.work_sessions.find_one({"_id": session_doc["_id"]})
        return _dict_to_work_session(updated_session)

    # In-memory fallback
    target_session = None
    for ws in _in_memory_work_sessions:
        if ws.get("agent") == agent and (ws.get("ticket_number") == ticket.ticket_number or ws.get("ticket_id") == ticket.id) and ws.get("is_active"):
            target_session = ws
            break

    if not target_session:
        raise ValueError(f"No active work session found for agent '{agent}' on ticket '{ticket.ticket_number}'.")

    try:
        start_dt = datetime.fromisoformat(target_session["start_time"].replace("Z", "+00:00"))
        duration = max(1, int((now_dt - start_dt).total_seconds()))
    except Exception:
        duration = 60

    target_session["stop_time"] = now_iso
    target_session["duration_seconds"] = duration
    target_session["is_active"] = False
    if note:
        target_session["note"] = note

    # Record history in in-memory ticket
    duration_fmt = f"{duration // 60}m {duration % 60}s"
    event = {
        "timestamp": now_iso,
        "actor": agent,
        "action": "Work Session",
        "note": f"Completed work session ({duration_fmt}). {note or ''}".strip(),
    }
    for t_doc in _in_memory_tickets:
        if t_doc["ticket_number"] == ticket.ticket_number:
            t_doc.setdefault("activity_history", []).append(event)
            break

    return _dict_to_work_session(target_session)


async def get_ticket_timer_status(ticket_id: str, agent: Optional[str] = None) -> TicketTimerStatusResponse:
    """Calculates cumulative duration and reports active timer for a ticket."""
    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        raise ValueError(f"Ticket '{ticket_id}' not found.")

    sessions: List[WorkSession] = []
    active_session: Optional[WorkSession] = None
    total_seconds = 0

    if _is_connected and _db is not None:
        cursor = _db.work_sessions.find({
            "$or": [{"ticket_id": ticket.id}, {"ticket_number": ticket.ticket_number}]
        }).sort("start_time", -1)
        async for doc in cursor:
            ws = _dict_to_work_session(doc)
            sessions.append(ws)
            if ws.is_active:
                active_session = ws
                try:
                    s_dt = datetime.fromisoformat(ws.start_time.replace("Z", "+00:00"))
                    total_seconds += max(0, int((datetime.now(timezone.utc) - s_dt).total_seconds()))
                except Exception:
                    pass
            else:
                total_seconds += ws.duration_seconds
    else:
        for ws_doc in _in_memory_work_sessions:
            if ws_doc.get("ticket_id") == ticket.id or ws_doc.get("ticket_number") == ticket.ticket_number:
                ws = _dict_to_work_session(ws_doc)
                sessions.append(ws)
                if ws.is_active:
                    active_session = ws
                    try:
                        s_dt = datetime.fromisoformat(ws.start_time.replace("Z", "+00:00"))
                        total_seconds += max(0, int((datetime.now(timezone.utc) - s_dt).total_seconds()))
                    except Exception:
                        pass
                else:
                    total_seconds += ws.duration_seconds

    # Human-readable formatting
    hrs = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hrs > 0:
        formatted = f"{hrs}h {mins}m"
    elif mins > 0:
        formatted = f"{mins}m {secs}s"
    else:
        formatted = f"{secs}s"

    is_agent_active = (active_session is not None and active_session.agent == agent) if agent else False

    return TicketTimerStatusResponse(
        ticket_id=ticket.id,
        active_session=active_session,
        total_duration_seconds=total_seconds,
        total_duration_formatted=formatted,
        total_duration_minutes=total_seconds // 60,
        is_agent_active=is_agent_active,
        sessions_count=len(sessions),
        sessions=sessions,
    )


async def get_all_work_sessions(agent: Optional[str] = None) -> List[WorkSession]:
    """Retrieves all recorded work sessions for the Timeline view."""
    await _try_auto_reconnect_if_needed()
    sessions: List[WorkSession] = []
    if _is_connected and _db is not None:
        try:
            query: Dict[str, Any] = {}
            if agent and agent != "ALL":
                query["agent"] = agent
            cursor = _db.work_sessions.find(query).sort("start_time", -1)
            async for doc in cursor:
                sessions.append(_dict_to_work_session(doc))
            return sessions
        except Exception as exc:
            _mark_atlas_unreachable(exc)
            raise DatabaseUnavailableError(
                f"Failed to query work sessions from MongoDB Atlas: {_sanitize_error_message(exc)}"
            ) from exc

    _require_atlas_for_read()

    for ws_doc in _in_memory_work_sessions:
        if agent and agent != "ALL" and ws_doc.get("agent") != agent:
            continue
        sessions.append(_dict_to_work_session(ws_doc))
    return sessions


# ── Knowledge Base Article Management ────────────────────────────────────────

async def create_kb_article(payload: KBArticleCreate) -> KBArticle:
    """Creates a new Knowledge Base article and returns the record."""
    _require_atlas_for_write()
    now_iso = datetime.now(timezone.utc).isoformat()
    if _is_connected and _db is not None:
        count = await _db.knowledge_base.count_documents({})
        art_id = f"kb-{101 + count}"
        doc = {
            "id": art_id,
            "title": payload.title.strip(),
            "category": payload.category.strip(),
            "read_time": payload.read_time,
            "excerpt": payload.excerpt.strip(),
            "content": payload.content.strip(),
            "tags": payload.tags,
            "updated_at": now_iso,
        }
        await _db.knowledge_base.insert_one(doc)
        return KBArticle(**doc)

    art_id = f"kb-{101 + len(_DEMO_KB_ARTICLES)}"
    doc = {
        "id": art_id,
        "title": payload.title.strip(),
        "category": payload.category.strip(),
        "read_time": payload.read_time,
        "excerpt": payload.excerpt.strip(),
        "content": payload.content.strip(),
        "tags": payload.tags,
        "updated_at": now_iso,
    }
    _DEMO_KB_ARTICLES.append(doc)
    return KBArticle(**doc)


async def update_kb_article(article_id: str, payload: KBArticleUpdate) -> Optional[KBArticle]:
    """Updates an existing KB article."""
    _require_atlas_for_write()
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_id = article_id.strip()

    update_dict: Dict[str, Any] = {"updated_at": now_iso}
    if payload.title is not None:
        update_dict["title"] = payload.title.strip()
    if payload.category is not None:
        update_dict["category"] = payload.category.strip()
    if payload.read_time is not None:
        update_dict["read_time"] = payload.read_time.strip()
    if payload.excerpt is not None:
        update_dict["excerpt"] = payload.excerpt.strip()
    if payload.content is not None:
        update_dict["content"] = payload.content.strip()
    if payload.tags is not None:
        update_dict["tags"] = payload.tags

    if _is_connected and _db is not None:
        await _db.knowledge_base.update_one({"id": clean_id}, {"$set": update_dict})
        doc = await _db.knowledge_base.find_one({"id": clean_id})
        return KBArticle(**{k: v for k, v in doc.items() if k != "_id"}) if doc else None

    for art in _DEMO_KB_ARTICLES:
        if art["id"] == clean_id:
            art.update(update_dict)
            return KBArticle(**art)
    return None

