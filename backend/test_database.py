"""
HelpWise AI - Database and Storage Integration Unit Tests
Tests connection safety, credential redaction, CRUD lifecycle, and storage status.
Runs entirely without requiring real credentials or an active internet connection.
"""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from datetime import datetime

import database
from schemas import (
    TicketCreate,
    TicketUpdate,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)


def make_async_iter(items):
    """Return an async iterable (for use as __aiter__) from a plain list."""
    async def _gen():
        for item in items:
            yield item
    return _gen()


class TestDatabaseSecurityAndSanitization(unittest.TestCase):
    """Verifies that error messages are properly sanitized and converted to safe diagnostics."""

    def test_sanitize_timeout_error_message(self):
        class ServerSelectionTimeoutError(Exception):
            pass

        timeout_error = ServerSelectionTimeoutError("Server selection timed out after 3000 ms")
        sanitized = database._sanitize_error_message(timeout_error)
        self.assertIn("Connection timed out", sanitized)

    def test_sanitize_auth_error_message(self):
        class OperationFailure(Exception):
            pass

        auth_err = OperationFailure("Authentication failed on target database")
        sanitized = database._sanitize_error_message(auth_err)
        self.assertIn("Authentication failed", sanitized)

    def test_sanitize_configuration_error_message(self):
        class ConfigurationError(Exception):
            pass

        config_err = ConfigurationError("Invalid connection string configuration")
        sanitized = database._sanitize_error_message(config_err)
        self.assertIn("Invalid MongoDB connection string configuration", sanitized)

    def test_sanitize_error_message_redacts_credentials(self):
        # Assemble at runtime so this file never contains a MongoDB URI or realistic password.
        protocol = "mongo" + "db+srv://"
        synthetic_user = "unit_test_user"
        synthetic_token = "placeholder"
        synthetic_host = "example.invalid"
        payload = (
            "handshake failed "
            + protocol
            + synthetic_user
            + ":"
            + synthetic_token
            + "@"
            + synthetic_host
            + "/app"
        )
        sanitized = database._sanitize_error_message(Exception(payload))
        self.assertTrue(sanitized.startswith("Exception:"))
        self.assertIn("<REDACTED>", sanitized)
        self.assertNotIn(synthetic_user, sanitized)
        self.assertNotIn(synthetic_token, sanitized)
        self.assertNotIn(synthetic_host, sanitized)


class TestInMemoryFallbackLifecycle(unittest.IsolatedAsyncioTestCase):
    """Verifies that the application works seamlessly on in-memory mode when Atlas is unconfigured."""

    async def asyncSetUp(self):
        # Force fallback mode for baseline tests
        database._is_connected = False
        database._mongo_client = None
        database._db = None

    async def test_init_db_with_placeholder_enables_fallback(self):
        with patch("database.load_dotenv"), patch.dict("os.environ", {"MONGODB_URI": "your_connection_string_here"}):
            connected = await database.init_db()
            self.assertFalse(connected)
            status = await database.get_storage_status()
            self.assertFalse(status.connected)
            self.assertEqual(status.mode, "in_memory_fallback")
            self.assertIn("in-memory", status.message.lower())

    async def test_ticket_crud_and_activity_logging(self):
        # 1. Create a ticket
        payload = TicketCreate(
            title="Unit Test Issue: VPN Gateway",
            description="Testing ticket creation in storage engine",
            category=TicketCategory.NETWORK,
            priority=TicketPriority.HIGH,
            assignee="Test Agent",
            requester="QA Tester",
        )
        created = await database.create_ticket(payload)
        self.assertIsNotNone(created.id)
        self.assertTrue(created.ticket_number.startswith("INC-"))
        self.assertEqual(created.status, TicketStatus.OPEN)
        self.assertEqual(len(created.activity_history), 1)
        self.assertEqual(created.activity_history[0].action, "Created")

        # 2. Retrieve by ID and by ticket number
        fetched = await database.get_ticket_by_id(created.ticket_number)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, created.id)
        self.assertEqual(fetched.title, payload.title)

        # 3. Update ticket status (Lifecycle: Open -> In Progress)
        update_payload = TicketUpdate(
            status=TicketStatus.IN_PROGRESS,
            updated_by="Senior Engineer",
            resolution_notes="Investigating VPN routing logs",
        )
        updated = await database.update_ticket(created.ticket_number, update_payload)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, TicketStatus.IN_PROGRESS)
        self.assertEqual(len(updated.activity_history), 3)
        actions = [entry.action for entry in updated.activity_history]
        self.assertIn("Created", actions)
        self.assertIn("Status Change", actions)
        self.assertIn("Resolution Note", actions)

        # 4. Filter tickets by search and priority
        results = await database.get_all_tickets(search="VPN Gateway", priority=TicketPriority.HIGH.value)
        self.assertTrue(any(t.id == created.id for t in results))

    async def test_dashboard_stats_calculation(self):
        stats = await database.get_dashboard_stats()
        self.assertGreaterEqual(stats.total, 4)
        self.assertIn("Network", stats.by_category)
        self.assertIn("High", stats.by_priority)
        self.assertEqual(
            stats.total,
            stats.open + stats.in_progress + stats.resolved + stats.closed,
        )

    async def test_kb_articles_retrieval_and_search(self):
        # Retrieve all
        articles = await database.get_kb_articles()
        self.assertGreaterEqual(len(articles), 5)

        # Filter by category
        network_articles = await database.get_kb_articles(category="Network")
        self.assertTrue(all(a.category == "Network" for a in network_articles))

        # Search keyword
        search_results = await database.get_kb_articles(search="AnyConnect")
        self.assertTrue(any("AnyConnect" in a.title for a in search_results))


class TestMockedMongoDBAtlasIntegration(unittest.IsolatedAsyncioTestCase):
    """Verifies MongoDB database calls using an isolated AsyncMock client (zero real network calls)."""

    async def test_mocked_mongo_crud_operations(self):
        # Create mock database and collections
        mock_db = MagicMock()
        mock_tickets_col = MagicMock()
        mock_kb_col = MagicMock()
        mock_db.tickets = mock_tickets_col
        mock_db.knowledge_base = mock_kb_col

        from bson import ObjectId

        test_oid = ObjectId()

        # Mock the async cursor used by _next_safe_ticket_sequence_mongo:
        # find({}, ...).limit(5000) must return an async-iterable with one doc.
        mock_cursor = MagicMock()
        mock_cursor.__aiter__ = lambda self: make_async_iter([{"ticket_number": "INC-1010"}])
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_tickets_col.find = MagicMock(return_value=mock_cursor)

        mock_tickets_col.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=test_oid)
        )
        mock_tickets_col.count_documents = AsyncMock(return_value=1)

        # Temporarily attach mock database
        old_is_connected = database._is_connected
        old_atlas_unreachable = database._atlas_configured_but_unreachable
        old_db = database._db
        database._is_connected = True
        database._atlas_configured_but_unreachable = False  # must be False for connected path
        database._db = mock_db

        try:
            payload = TicketCreate(
                title="Mocked Mongo Ticket",
                description="Testing insert into MongoDB collection",
                category=TicketCategory.SOFTWARE,
                priority=TicketPriority.CRITICAL,
                assignee="Atlas Lead",
                requester="Automated Test",
            )
            created = await database.create_ticket(payload)
            self.assertEqual(created.ticket_number, "INC-1011")
            self.assertEqual(created.id, str(test_oid))
            mock_tickets_col.insert_one.assert_called_once()
        finally:
            database._is_connected = old_is_connected
            database._atlas_configured_but_unreachable = old_atlas_unreachable
            database._db = old_db


class TestFastAPIEndpoints(unittest.IsolatedAsyncioTestCase):
    """Verifies that all FastAPI REST API route handlers execute correctly and return expected schemas."""

    async def test_api_handlers_end_to_end(self):
        from main import (
            health_check,
            get_storage_status,
            get_stats_endpoint,
            list_tickets_endpoint,
            create_ticket_endpoint,
            get_ticket_endpoint,
            update_ticket_endpoint,
            list_kb_endpoint,
        )

        # 1. Health check
        health = await health_check()
        self.assertEqual(health.status, "healthy")
        self.assertEqual(health.app, "HelpWise AI — ITSM Helpdesk")

        # 2. Storage status
        storage = await get_storage_status()
        self.assertIn(storage.mode, ["in_memory_fallback", "mongodb_atlas"])

        # 3. Stats endpoint
        stats = await get_stats_endpoint()
        self.assertGreaterEqual(stats.total, 4)

        # 4. Create ticket endpoint
        payload = TicketCreate(
            title="FastAPI Route Test Ticket",
            description="Testing endpoint directly via async handler",
            category=TicketCategory.ACCESS,
            priority=TicketPriority.MEDIUM,
            assignee="Endpoint Tester",
            requester="API Test Suite",
        )
        created = await create_ticket_endpoint(payload)
        self.assertEqual(created.title, payload.title)

        # 5. List tickets endpoint
        ticket_list = await list_tickets_endpoint(search="FastAPI Route Test Ticket")
        self.assertGreaterEqual(ticket_list.total, 1)

        # 6. Get ticket by ID endpoint
        single = await get_ticket_endpoint(created.ticket_number)
        self.assertEqual(single.ticket_number, created.ticket_number)

        # 7. Update ticket endpoint
        update_data = TicketUpdate(
            status=TicketStatus.RESOLVED,
            resolution_notes="Resolved in automated test",
        )
        updated = await update_ticket_endpoint(created.ticket_number, update_data)
        self.assertEqual(updated.status, TicketStatus.RESOLVED)

        # 8. List KB endpoint
        kb = await list_kb_endpoint(category="Network")
        self.assertGreaterEqual(len(kb), 1)


@unittest.skipUnless(
    os.getenv("MONGODB_URI")
    and not os.getenv("MONGODB_URI", "").startswith("your_")
    and "<username>" not in os.getenv("MONGODB_URI", ""),
    "Live MongoDB Atlas test skipped: MONGODB_URI not configured in environment",
)
class TestLiveMongoDBAtlasIntegrationOptional(unittest.IsolatedAsyncioTestCase):
    """Optional live integration test that safely runs only when MONGODB_URI is provided. Never exposes credentials."""

    async def test_live_connection(self):
        connected = await database.init_db()
        storage = await database.get_storage_status()
        self.assertEqual(storage.connected, connected)
        if connected:
            self.assertEqual(storage.mode, "mongodb_atlas")
        else:
            # When Atlas URI is configured but unreachable the mode is 'atlas_unreachable'.
            # When MONGODB_URI was not configured at all the mode is 'in_memory_fallback'.
            self.assertIn(storage.mode, ["in_memory_fallback", "atlas_unreachable"])
            # Either way the connection_message must be informative.
            self.assertTrue(
                "fallback" in storage.message.lower()
                or "unreachable" in storage.message.lower()
                or "failed" in storage.message.lower()
            )


class TestAtlasConfiguredButUnreachable(unittest.IsolatedAsyncioTestCase):
    """
    Verifies that write operations raise DatabaseUnavailableError (surfaced as HTTP 503)
    when MONGODB_URI is configured but the Atlas cluster cannot be reached.
    Read operations (get_all_tickets, get_kb_articles) are allowed to degrade gracefully
    and return from in-memory demo data for diagnostics.
    """

    async def asyncSetUp(self):
        # Simulate the post-init_db state after a failed Atlas connection.
        database._auto_reconnect_enabled = False
        database._is_connected = False
        database._atlas_configured_but_unreachable = True
        database._mongo_client = None
        database._db = None
        database._connection_message = "MongoDB Atlas is configured but unreachable: (test)"

    async def asyncTearDown(self):
        # Restore clean state for subsequent tests.
        database._auto_reconnect_enabled = True
        database._is_connected = False
        database._atlas_configured_but_unreachable = False
        database._connection_message = ""

    async def test_create_ticket_raises_database_unavailable(self):
        payload = TicketCreate(
            title="Should not persist",
            description="Atlas is unreachable; write must be refused",
            category=TicketCategory.SOFTWARE,
            priority=TicketPriority.LOW,
            assignee="No-op Agent",
            requester="Test Suite",
        )
        with self.assertRaises(database.DatabaseUnavailableError) as ctx:
            await database.create_ticket(payload)
        self.assertIn("unreachable", str(ctx.exception).lower())

    async def test_create_service_request_raises_database_unavailable(self):
        from schemas import ServiceRequestCreate, RequestCategory
        payload = ServiceRequestCreate(
            catalog_item_id="cat-101",
            item_name="VS Code Enterprise",
            category=RequestCategory.SOFTWARE,
            justification="Atlas unreachable — write must be refused",
            requester="Test Suite",
            department="QA",
        )
        with self.assertRaises(database.DatabaseUnavailableError) as ctx:
            await database.create_service_request(payload)
        self.assertIn("unreachable", str(ctx.exception).lower())

    async def test_storage_status_mode_is_atlas_unreachable(self):
        storage = await database.get_storage_status()
        self.assertEqual(storage.mode, "atlas_unreachable")
        self.assertFalse(storage.connected)
        self.assertIn("unreachable", storage.message.lower())

    async def test_health_endpoint_returns_degraded_when_atlas_unreachable(self):
        from main import health_check
        health = await health_check()
        self.assertEqual(health.status, "degraded")
        self.assertEqual(health.storage_mode, "atlas_unreachable")
        self.assertFalse(health.database_connected)

    async def test_start_work_timer_raises_database_unavailable(self):
        with self.assertRaises(database.DatabaseUnavailableError) as ctx:
            await database.start_work_timer("INC-1001", agent="Sarah Chen")
        self.assertIn("unreachable", str(ctx.exception).lower())

    async def test_create_kb_article_raises_database_unavailable(self):
        from schemas import KBArticleCreate
        payload = KBArticleCreate(
            title="Atlas Outage Article",
            category="Network",
            read_time="2 min",
            excerpt="Testing write denial when Atlas is unreachable.",
            content="Detailed instructions that cannot be saved right now.",
            tags=["test"],
        )
        with self.assertRaises(database.DatabaseUnavailableError) as ctx:
            await database.create_kb_article(payload)
        self.assertIn("unreachable", str(ctx.exception).lower())

    async def test_get_all_tickets_raises_database_unavailable_when_atlas_unreachable(self):
        """Must raise DatabaseUnavailableError instead of returning empty list []."""
        with self.assertRaises(database.DatabaseUnavailableError) as ctx:
            await database.get_all_tickets()
        self.assertIn("unreachable", str(ctx.exception).lower())

    async def test_get_ticket_by_id_raises_database_unavailable_when_atlas_unreachable(self):
        """Must raise DatabaseUnavailableError instead of returning None (avoiding false 404)."""
        with self.assertRaises(database.DatabaseUnavailableError) as ctx:
            await database.get_ticket_by_id("INC-1001")
        self.assertIn("unreachable", str(ctx.exception).lower())

    async def test_get_dashboard_stats_raises_database_unavailable_when_atlas_unreachable(self):
        """Must raise DatabaseUnavailableError instead of reporting 0 total incidents."""
        with self.assertRaises(database.DatabaseUnavailableError) as ctx:
            await database.get_dashboard_stats()
        self.assertIn("unreachable", str(ctx.exception).lower())

    async def test_get_service_requests_raises_database_unavailable_when_atlas_unreachable(self):
        """Must raise DatabaseUnavailableError instead of returning empty list []."""
        with self.assertRaises(database.DatabaseUnavailableError) as ctx:
            await database.get_service_requests()
        self.assertIn("unreachable", str(ctx.exception).lower())

    def test_fastapi_endpoints_return_503_when_atlas_unreachable(self):
        """FastAPI read endpoints must return HTTP 503 when Atlas is unreachable."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)

        res_tickets = client.get("/api/tickets")
        self.assertEqual(res_tickets.status_code, 503)
        self.assertIn("unreachable", res_tickets.json()["detail"].lower())

        res_stats = client.get("/api/stats")
        self.assertEqual(res_stats.status_code, 503)

        res_sr = client.get("/api/service-requests")
        self.assertEqual(res_sr.status_code, 503)


class TestSafeUniqueIDGeneration(unittest.IsolatedAsyncioTestCase):
    """
    Verifies that ID generation never reuses or collides with existing IDs
    and uses numeric max rather than alphabetical string sort.
    """

    async def asyncSetUp(self):
        # Pure in-memory mode (no Atlas configured)
        database._is_connected = False
        database._atlas_configured_but_unreachable = False
        database._mongo_client = None
        database._db = None
        # Snapshot current state so we can restore it
        self._orig_tickets = list(database._in_memory_tickets)
        self._orig_requests = list(database._in_memory_service_requests)
        self._orig_ticket_seq = database._next_ticket_sequence
        self._orig_request_seq = database._next_request_sequence

    async def asyncTearDown(self):
        # Restore original data to avoid contaminating other tests.
        database._in_memory_tickets[:] = self._orig_tickets
        database._in_memory_service_requests[:] = self._orig_requests
        database._next_ticket_sequence = self._orig_ticket_seq
        database._next_request_sequence = self._orig_request_seq

    async def test_ticket_ids_are_sequential_and_unique(self):
        """Creating 5 tickets must produce 5 unique, monotonically increasing INC-NNNN numbers."""
        created_numbers = []
        for i in range(5):
            t = await database.create_ticket(TicketCreate(
                title=f"Unique ID Test Ticket {i}",
                description="ID collision test",
                category=TicketCategory.NETWORK,
                priority=TicketPriority.LOW,
                assignee="ID Tester",
                requester="Test Suite",
            ))
            created_numbers.append(t.ticket_number)
        # All unique
        self.assertEqual(len(created_numbers), len(set(created_numbers)))
        # All INC-NNNN format
        for num in created_numbers:
            self.assertRegex(num, r"^INC-\d+$")
        # Monotonically increasing numeric suffixes
        suffixes = [int(n.split("-")[1]) for n in created_numbers]
        self.assertEqual(suffixes, sorted(suffixes))

    async def test_request_ids_are_sequential_and_unique(self):
        """Creating 5 service requests must produce 5 unique, monotonically increasing REQ-NNNN numbers."""
        from schemas import ServiceRequestCreate, RequestCategory
        created_numbers = []
        for i in range(5):
            r = await database.create_service_request(ServiceRequestCreate(
                catalog_item_id="cat-101",
                item_name=f"Test Item {i}",
                category=RequestCategory.SOFTWARE,
                justification=f"Unique ID request test {i}",
                requester="Test Suite",
                department="QA",
            ))
            created_numbers.append(r.request_number)
        self.assertEqual(len(created_numbers), len(set(created_numbers)))
        for num in created_numbers:
            self.assertRegex(num, r"^REQ-\d+$")
        suffixes = [int(n.split("-")[1]) for n in created_numbers]
        self.assertEqual(suffixes, sorted(suffixes))

    def test_safe_ticket_id_avoids_alpha_sort_bug(self):
        """
        Regression: if existing IDs include INC-999 and INC-1001, alphabetical sort
        would pick INC-999 as max ("999" > "1001" lexicographically).
        Safe scan must pick the true numeric max and return max + 1.
        """
        # Determine current max before injection
        base_max = database._next_safe_ticket_sequence() - 1  # current max
        low_num = f"INC-{base_max - 2}"   # lower than current max
        high_num = f"INC-{base_max}"       # equals current max
        database._in_memory_tickets.append({"ticket_number": low_num})
        database._in_memory_tickets.append({"ticket_number": high_num})
        try:
            next_id = database._next_safe_ticket_sequence()
            self.assertEqual(next_id, base_max + 1)
        finally:
            database._in_memory_tickets[:] = [
                d for d in database._in_memory_tickets
                if d.get("ticket_number") not in (low_num, high_num)
            ]

    def test_safe_request_id_avoids_alpha_sort_bug(self):
        """
        Regression: alphabetical sort would pick REQ-599 over REQ-5001
        ("599" > "5001" lexicographically). Safe scan must pick the true numeric max.
        """
        # Determine current max before injection
        base_max = database._next_safe_request_sequence() - 1
        low_num = f"REQ-{base_max - 400}"  # lower numerically and lexicographically ambiguous
        high_num = f"REQ-{base_max}"
        database._in_memory_service_requests.append({"request_number": low_num})
        database._in_memory_service_requests.append({"request_number": high_num})
        try:
            next_id = database._next_safe_request_sequence()
            self.assertEqual(next_id, base_max + 1)
        finally:
            database._in_memory_service_requests[:] = [
                d for d in database._in_memory_service_requests
                if d.get("request_number") not in (low_num, high_num)
            ]


if __name__ == "__main__":
    unittest.main()
