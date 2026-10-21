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
        with patch.dict("os.environ", {"MONGODB_URI": "your_connection_string_here"}):
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

        # Mock latest ticket lookup
        mock_tickets_col.find_one = AsyncMock(
            return_value={"ticket_number": "INC-1010"}
        )
        mock_tickets_col.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id=test_oid)
        )
        mock_tickets_col.count_documents = AsyncMock(return_value=1)

        # Temporarily attach mock database
        old_is_connected = database._is_connected
        old_db = database._db
        database._is_connected = True
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
        status = await database.get_storage_status()
        self.assertEqual(status.connected, connected)
        if connected:
            self.assertEqual(status.mode, "mongodb_atlas")
        else:
            self.assertEqual(status.mode, "in_memory_fallback")
            self.assertTrue("fell back" in status.message.lower() or "fallback" in status.message.lower())


if __name__ == "__main__":
    unittest.main()

