"""
Comprehensive test suite for HelpWise AI ITSM Platform Features:
- User Personas & Ticket Ownership
- Service Requests & Catalogue Lifecycle
- Work Timers & Active Timer Enforcement
- Self-Heal Diagnostics
- ServiceNow Integration Adapter
- All-Rounder Chatbot Intent Routing
"""

import os
import unittest
from unittest.mock import patch
import asyncio

os.environ["HELPWISE_CHROMA_DIR"] = ":memory:"
os.environ["HELPWISE_LLM_ENABLED"] = "1"

from fastapi.testclient import TestClient
from main import app
import database
from schemas import (
    UserRole,
    TicketCreate,
    TicketCategory,
    TicketPriority,
    ServiceRequestCreate,
    RequestCategory,
    RequestStatus,
    ServiceRequestStatusUpdate,
    TimerActionRequest,
)


class TestITSMFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database._is_connected = False
        database._mongo_client = None
        database._db = None

    def setUp(self):
        self.client = TestClient(app)

    def test_user_personas_endpoint(self):
        resp = self.client.get("/api/users/personas")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 3)
        roles = [p["role"] for p in data]
        self.assertIn("Employee", roles)
        self.assertIn("Support Agent", roles)
        self.assertIn("Administrator", roles)

    def test_catalog_endpoint(self):
        resp = self.client.get("/api/catalog")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertGreaterEqual(len(items), 6)
        names = [i["name"] for i in items]
        self.assertTrue(any("Docker" in n for n in names))
        self.assertTrue(any("JetBrains" in n for n in names))

    def test_service_request_lifecycle(self):
        # 1. Create request
        create_payload = {
            "catalog_item_id": "cat-103",
            "item_name": "Docker Desktop Commercial License",
            "category": "Software & Licenses",
            "justification": "Local microservices container development",
            "requester": "Alex Morgan",
            "department": "Engineering",
        }
        res = self.client.post("/api/service-requests", json=create_payload)
        self.assertEqual(res.status_code, 201)
        sr = res.json()
        self.assertTrue(sr["request_number"].startswith("REQ-"))
        self.assertEqual(sr["requester"], "Alex Morgan")
        req_id = sr["request_number"]

        # 2. Filter requests by requester
        filter_res = self.client.get(f"/api/service-requests?requester=Alex Morgan")
        self.assertEqual(filter_res.status_code, 200)
        reqs = filter_res.json()
        self.assertTrue(any(r["request_number"] == req_id for r in reqs))

        # 3. Approve request (Admin / Manager action)
        patch_payload = {
            "status": "Approved",
            "notes": "Approved for project work.",
            "actor": "Marcus Vance",
        }
        approve_res = self.client.patch(f"/api/service-requests/{req_id}/status", json=patch_payload)
        self.assertEqual(approve_res.status_code, 200)
        approved_sr = approve_res.json()
        self.assertEqual(approved_sr["status"], "Approved")
        self.assertEqual(approved_sr["approver"], "Marcus Vance")

    def test_work_timer_start_and_stop_lifecycle(self):
        # 1. Start timer on INC-1001 for Sarah Chen
        start_payload = {"agent": "Sarah Chen", "note": "Initial investigation"}
        res1 = self.client.post("/api/tickets/INC-1001/timer/start", json=start_payload)
        self.assertEqual(res1.status_code, 200)
        ws1 = res1.json()
        self.assertTrue(ws1["is_active"])
        self.assertEqual(ws1["agent"], "Sarah Chen")

        # 2. Enforce: Attempting to start a second timer for Sarah Chen on INC-1002 must be rejected
        res2 = self.client.post("/api/tickets/INC-1002/timer/start", json=start_payload)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already has an active work timer", res2.json()["detail"])

        # 3. Stop active timer
        stop_payload = {"agent": "Sarah Chen", "note": "Completed root cause analysis"}
        res3 = self.client.post("/api/tickets/INC-1001/timer/stop", json=stop_payload)
        self.assertEqual(res3.status_code, 200)
        ws3 = res3.json()
        self.assertFalse(ws3["is_active"])
        self.assertGreaterEqual(ws3["duration_seconds"], 1)

        # 4. Timer status for ticket
        status_res = self.client.get("/api/tickets/INC-1001/timer/status")
        self.assertEqual(status_res.status_code, 200)
        t_stat = status_res.json()
        self.assertGreater(t_stat["total_duration_seconds"], 0)
        self.assertIsNone(t_stat["active_session"])

    def test_diagnostics_endpoints(self):
        # Network
        net_res = self.client.get("/api/diagnostics/network")
        self.assertEqual(net_res.status_code, 200)
        self.assertIn("steps", net_res.json())

        # System
        sys_res = self.client.get("/api/diagnostics/system")
        self.assertEqual(sys_res.status_code, 200)
        self.assertIn("steps", sys_res.json())

        # Disk
        disk_res = self.client.get("/api/diagnostics/disk")
        self.assertEqual(disk_res.status_code, 200)
        self.assertIn("steps", disk_res.json())

    def test_servicenow_status_and_simulation(self):
        # Status
        st_res = self.client.get("/api/servicenow/status")
        self.assertEqual(st_res.status_code, 200)
        info = st_res.json()
        self.assertIn("mode", info)

        # Verify endpoint in simulation mode
        v_res = self.client.get("/api/servicenow/verify")
        self.assertEqual(v_res.status_code, 200)
        self.assertFalse(v_res.json()["authenticated"])

        # Fetch non-existent/simulated incident
        f_res = self.client.get("/api/servicenow/incident/INC0010001")
        self.assertEqual(f_res.status_code, 200)
        self.assertFalse(f_res.json()["found"])

        # Sync ticket (Simulation mode)
        sync_res = self.client.post("/api/servicenow/sync/INC-1001")
        self.assertEqual(sync_res.status_code, 200)
        sync_data = sync_res.json()
        self.assertTrue(sync_data["synced"])
        self.assertIn("sys_id", sync_data)
        self.assertTrue(sync_data["number"].startswith("INC"))
        self.assertIn("payload", sync_data)

    def test_servicenow_live_create_mocked(self):
        """Validates real Table API live incident creation with mocked HTTP response."""
        mock_response = {
            "result": {
                "sys_id": "mock_sys_id_9999",
                "number": "INC0010099",
                "state": "1",
            }
        }
        with patch("servicenow._get_config") as mock_cfg:
            mock_cfg.return_value = {
                "instance_url": "https://dev461045.service-now.com",
                "user": "admin",
                "password": "mock_password",
                "configured": True,
            }
            with patch("httpx.AsyncClient.post") as mock_post:
                class MockResponse:
                    status_code = 201
                    def json(self):
                        return mock_response
                mock_post.return_value = MockResponse()

                sync_res = self.client.post("/api/servicenow/sync/INC-1001")
                self.assertEqual(sync_res.status_code, 200)
                data = sync_res.json()
                self.assertEqual(data["mode"], "live")
                self.assertTrue(data["synced"])
                self.assertEqual(data["number"], "INC0010099")
                self.assertEqual(data["sys_id"], "mock_sys_id_9999")
                self.assertEqual(data["state"], "New")

    def test_servicenow_live_fetch_mocked(self):
        """Validates real Table API live incident lookup with mocked HTTP response."""
        mock_response = {
            "result": [
                {
                    "number": "INC0010099",
                    "short_description": "Cannot connect to VPN",
                    "state": "In Progress",
                    "priority": "2 - High",
                    "category": "network",
                }
            ]
        }
        with patch("servicenow._get_config") as mock_cfg:
            mock_cfg.return_value = {
                "instance_url": "https://dev461045.service-now.com",
                "user": "admin",
                "password": "mock_password",
                "configured": True,
            }
            with patch("httpx.AsyncClient.get") as mock_get:
                class MockResponse:
                    status_code = 200
                    def json(self):
                        return mock_response
                mock_get.return_value = MockResponse()

                fetch_res = self.client.get("/api/servicenow/incident/INC0010099")
                self.assertEqual(fetch_res.status_code, 200)
                data = fetch_res.json()
                self.assertEqual(data["mode"], "live")
                self.assertTrue(data["found"])
                self.assertEqual(data["number"], "INC0010099")
                self.assertEqual(data["short_description"], "Cannot connect to VPN")

    def test_servicenow_live_auth_error_mocked(self):
        """Validates graceful 401 handling without exposing credentials."""
        with patch("servicenow._get_config") as mock_cfg:
            mock_cfg.return_value = {
                "instance_url": "https://dev461045.service-now.com",
                "user": "admin",
                "password": "wrong_password",
                "configured": True,
            }
            with patch("httpx.AsyncClient.post") as mock_post:
                class MockResponse:
                    status_code = 401
                    def json(self):
                        return {"error": {"message": "User Not Authenticated"}}
                mock_post.return_value = MockResponse()

                sync_res = self.client.post("/api/servicenow/sync/INC-1001")
                self.assertEqual(sync_res.status_code, 200)
                data = sync_res.json()
                self.assertEqual(data["mode"], "live")
                self.assertFalse(data["synced"])
                self.assertEqual(data["error"], "authentication_failed")
                self.assertIn("401", data["message"])

    def test_chatbot_greeting_intent(self):
        resp = self.client.post("/api/kb/chat", json={"message": "Hello!", "history": []})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "greeting")
        self.assertIn("HelpWise AI", data["message"])
        self.assertEqual(data["matched_articles"], [])

    def test_chatbot_ticket_status_intent(self):
        resp = self.client.post(
            "/api/kb/chat",
            json={"message": "What is the status of my tickets?", "history": []},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "ticket_status")
        self.assertTrue("ticket" in data["message"].lower())

    def test_chatbot_service_request_proposal_and_confirmation(self):
        # 1. User asks for Docker Desktop
        resp1 = self.client.post(
            "/api/kb/chat",
            json={"message": "I need Docker Desktop for my development work", "history": []},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertEqual(data1["intent"], "service_request")
        self.assertIsNotNone(data1["action_proposed"])
        self.assertEqual(data1["action_proposed"]["catalog_item_id"], "cat-103")

        # 2. User confirms
        history = [
            {"role": "user", "content": "I need Docker Desktop for my development work"},
            {"role": "assistant", "content": data1["message"]},
        ]
        resp2 = self.client.post(
            "/api/kb/chat",
            json={"message": "Yes, confirm creation please", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertIsNotNone(data2["action_result"])
        self.assertEqual(data2["action_result"]["record_type"], "service_request")
        self.assertTrue(data2["action_result"]["record_id"].startswith("REQ-"))

    def test_frontend_route_aliases_and_diagnostics(self):
        # 1. /api/service-catalog alias
        cat_res = self.client.get("/api/service-catalog")
        self.assertEqual(cat_res.status_code, 200)
        self.assertGreaterEqual(len(cat_res.json()), 6)

        # 2. /api/diagnostics/run POST
        diag_res = self.client.post("/api/diagnostics/run")
        self.assertEqual(diag_res.status_code, 200)
        d_data = diag_res.json()
        self.assertIn("checks", d_data)
        self.assertEqual(len(d_data["checks"]), 4)
        check_categories = [c["category"] for c in d_data["checks"]]
        self.assertIn("ServiceNow Table API Adapter", check_categories)

        # 3. Work sessions start/stop aliases & active-timer
        # Start
        start_res = self.client.post(
            "/api/tickets/INC-1002/work-sessions/start",
            json={"agent": "David Miller", "note": "Alias start test"},
        )
        self.assertEqual(start_res.status_code, 200)
        self.assertTrue(start_res.json()["is_active"])

        # Active timer query
        active_res = self.client.get("/api/tickets/active-timer?agent=David%20Miller")
        self.assertEqual(active_res.status_code, 200)
        self.assertIsNotNone(active_res.json()["active_timer"])
        self.assertEqual(active_res.json()["active_timer"]["agent"], "David Miller")

        # Timer status alias with agent param
        stat_res = self.client.get("/api/tickets/INC-1002/timer-status?agent=David%20Miller")
        self.assertEqual(stat_res.status_code, 200)
        self.assertTrue(stat_res.json()["is_agent_active"])

        # Stop
        stop_res = self.client.post(
            "/api/tickets/INC-1002/work-sessions/stop",
            json={"agent": "David Miller", "note": "Alias stop test"},
        )
        self.assertEqual(stop_res.status_code, 200)
        self.assertFalse(stop_res.json()["is_active"])

        # 4. PATCH /api/service-requests/{id} alias
        # Create request first
        sr_create = self.client.post(
            "/api/service-requests",
            json={
                "catalog_item_id": "cat-101",
                "item_name": "Standard Laptop",
                "category": "Hardware & Equipment",
                "business_justification": "Hardware replacement for engineer",
                "requester": "Priya Sharma",
            },
        )
        self.assertEqual(sr_create.status_code, 201)
        sr_num = sr_create.json()["request_number"]

        # Patch via alias
        patch_res = self.client.patch(
            f"/api/service-requests/{sr_num}",
            json={"status": "Approved", "rejection_reason": "Approved by manager", "actor": "Marcus Vance"},
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["status"], "Approved")

        # 5. POST /api/kb/articles alias
        kb_res = self.client.post(
            "/api/kb/articles",
            json={
                "title": "Configuring PostgreSQL local dev environment",
                "category": "Database",
                "read_time": "4 min",
                "excerpt": "Guide to setting up local PostgreSQL instance on Windows.",
                "content": "Follow these steps to initialize PostgreSQL database cluster and create local roles.",
                "tags": ["postgresql", "database", "setup"],
            },
        )
        self.assertEqual(kb_res.status_code, 201)
        self.assertIn("id", kb_res.json())

    def test_conversational_followups_and_scenarios_a_to_h(self):
        # Scenario A: User: "My VPN keeps disconnecting. How can I troubleshoot it?"
        history = []
        resp_a = self.client.post(
            "/api/kb/chat",
            json={"message": "My VPN keeps disconnecting. How can I troubleshoot it?", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp_a.status_code, 200)
        data_a = resp_a.json()
        self.assertEqual(data_a["intent"], "knowledge_search")
        self.assertGreaterEqual(len(data_a["matched_articles"]), 1)
        self.assertEqual(data_a["matched_articles"][0]["id"], "kb-101")
        history.append({"role": "user", "content": "My VPN keeps disconnecting. How can I troubleshoot it?"})
        history.append({"role": "assistant", "content": data_a["message"]})

        # Scenario B: User: "I tried that, but it still doesn't work."
        resp_b = self.client.post(
            "/api/kb/chat",
            json={"message": "I tried that, but it still doesn't work.", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp_b.status_code, 200)
        data_b = resp_b.json()
        self.assertEqual(data_b["intent"], "troubleshooting_failed")
        self.assertIn("hotspot", data_b["message"].lower())
        self.assertGreaterEqual(len(data_b["matched_articles"]), 1)
        self.assertEqual(data_b["matched_articles"][0]["id"], "kb-101")
        history.append({"role": "user", "content": "I tried that, but it still doesn't work."})
        history.append({"role": "assistant", "content": data_b["message"]})

        # Scenario C: User: "What should I do next?"
        resp_c = self.client.post(
            "/api/kb/chat",
            json={"message": "What should I do next?", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp_c.status_code, 200)
        data_c = resp_c.json()
        self.assertEqual(data_c["intent"], "what_next")
        self.assertTrue("diagnostics" in data_c["message"].lower() or "ticket" in data_c["message"].lower())
        self.assertEqual(data_c["matched_articles"][0]["id"], "kb-101")
        history.append({"role": "user", "content": "What should I do next?"})
        history.append({"role": "assistant", "content": data_c["message"]})

        # Scenario D: User: "Explain that in simple terms."
        resp_d = self.client.post(
            "/api/kb/chat",
            json={"message": "Explain that in simple terms.", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp_d.status_code, 200)
        data_d = resp_d.json()
        self.assertEqual(data_d["intent"], "explain_simply")
        self.assertIn("tunnel", data_d["message"].lower())
        self.assertEqual(data_d["matched_articles"][0]["id"], "kb-101")
        history.append({"role": "user", "content": "Explain that in simple terms."})
        history.append({"role": "assistant", "content": data_d["message"]})

        # Scenario E: User: "I need Docker Desktop for development."
        resp_e = self.client.post(
            "/api/kb/chat",
            json={"message": "I need Docker Desktop for development.", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp_e.status_code, 200)
        data_e = resp_e.json()
        self.assertEqual(data_e["intent"], "service_request")
        self.assertIsNotNone(data_e["action_proposed"])
        self.assertEqual(data_e["action_proposed"]["catalog_item_id"], "cat-103")
        history.append({"role": "user", "content": "I need Docker Desktop for development."})
        history.append({"role": "assistant", "content": data_e["message"]})

        # Scenario F1: User: "Yes, confirm." with valid pending proposal -> Creates request
        resp_f1 = self.client.post(
            "/api/kb/chat",
            json={"message": "Yes, confirm.", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp_f1.status_code, 200)
        data_f1 = resp_f1.json()
        self.assertEqual(data_f1["intent"], "service_request")
        self.assertIsNotNone(data_f1["action_result"])
        self.assertTrue(data_f1["action_result"]["record_id"].startswith("REQ-"))

        # Scenario F2: User says "Yes, confirm." when NO pending proposal exists (fresh chat)
        resp_f2 = self.client.post(
            "/api/kb/chat",
            json={"message": "Yes, confirm.", "history": []},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp_f2.status_code, 200)
        data_f2 = resp_f2.json()
        self.assertEqual(data_f2["intent"], "confirm_without_proposal")
        self.assertIsNone(data_f2["action_result"])
        self.assertIn("no pending ticket or service request", data_f2["message"].lower())

        # Scenario G: User: "What is the status of my tickets?"
        resp_g = self.client.post(
            "/api/kb/chat",
            json={"message": "What is the status of my tickets?", "history": []},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp_g.status_code, 200)
        data_g = resp_g.json()
        self.assertEqual(data_g["intent"], "ticket_status")
        self.assertIn("tickets", data_g["message"].lower())

        # Scenario H: User: "Thanks, that helped."
        resp_h = self.client.post(
            "/api/kb/chat",
            json={"message": "Thanks, that helped.", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(resp_h.status_code, 200)
        data_h = resp_h.json()
        self.assertEqual(data_h["intent"], "gratitude")
        self.assertIn("welcome", data_h["message"].lower())

    def test_stateful_troubleshooting_progression_scenario_a(self):
        """Validates Scenario A multi-turn progression through step 1, step 2, simplify, step 3, incident proposal, confirmation, and duplicate protection."""
        history = []
        # Turn 1: Initial report
        r1 = self.client.post("/api/kb/chat", json={"message": "My VPN keeps disconnecting.", "history": history})
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()
        self.assertEqual(d1["intent"], "knowledge_search")
        self.assertEqual(d1["matched_articles"][0]["id"], "kb-101")
        history.append({"role": "user", "content": "My VPN keeps disconnecting."})
        history.append({"role": "assistant", "content": d1["message"]})

        # Turn 2: Step 1 failed -> moves to Step 2 (isolation)
        r2 = self.client.post("/api/kb/chat", json={"message": "I tried that, but it still does not work.", "history": history})
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertEqual(d2["intent"], "troubleshooting_failed")
        self.assertIn("hotspot", d2["message"].lower())
        history.append({"role": "user", "content": "I tried that, but it still does not work."})
        history.append({"role": "assistant", "content": d2["message"]})

        # Turn 3: Explain simply -> contextual explanation of isolation
        r3 = self.client.post("/api/kb/chat", json={"message": "Can you explain it simply?", "history": history})
        self.assertEqual(r3.status_code, 200)
        d3 = r3.json()
        self.assertEqual(d3["intent"], "explain_simply")
        self.assertEqual(d3["generation_mode"], "simplified_explanation")
        self.assertIn("hotspot", d3["message"].lower())
        history.append({"role": "user", "content": "Can you explain it simply?"})
        history.append({"role": "assistant", "content": d3["message"]})

        # Turn 4: Step 2 failed -> moves to Step 3 (settings / diagnostics)
        r4 = self.client.post("/api/kb/chat", json={"message": "That didn't help either.", "history": history})
        self.assertEqual(r4.status_code, 200)
        d4 = r4.json()
        self.assertEqual(d4["intent"], "troubleshooting_failed")
        self.assertIn("passthrough", d4["message"].lower())
        history.append({"role": "user", "content": "That didn't help either."})
        history.append({"role": "assistant", "content": d4["message"]})

        # Turn 5: User asks to open an incident -> intake proposal with context
        r5 = self.client.post("/api/kb/chat", json={"message": "Can you open an incident?", "history": history})
        self.assertEqual(r5.status_code, 200)
        d5 = r5.json()
        self.assertEqual(d5["intent"], "incident_intake")
        self.assertEqual(d5["generation_mode"], "ticket_intake_proposal")
        self.assertIsNotNone(d5["action_proposed"])
        history.append({"role": "user", "content": "Can you open an incident?"})
        history.append({"role": "assistant", "content": d5["message"]})

        # Turn 6: Confirm creation -> exactly 1 ticket created
        r6 = self.client.post("/api/kb/chat", json={"message": "Yes, please confirm.", "history": history})
        self.assertEqual(r6.status_code, 200)
        d6 = r6.json()
        self.assertIsNotNone(d6["action_result"])
        self.assertTrue(d6["action_result"]["record_id"].startswith("INC-"))
        created_id = d6["action_result"]["record_id"]
        history.append({"role": "user", "content": "Yes, please confirm."})
        history.append({"role": "assistant", "content": d6["message"]})

        # Turn 7: Duplicate confirmation -> blocked, no second ticket
        r7 = self.client.post("/api/kb/chat", json={"message": "Yes, please confirm.", "history": history})
        self.assertEqual(r7.status_code, 200)
        d7 = r7.json()
        self.assertEqual(d7["intent"], "confirm_without_proposal")
        self.assertEqual(d7["generation_mode"], "already_confirmed")
        self.assertIsNone(d7["action_result"])
        self.assertIn(created_id, d7["message"])

    def test_software_request_duplicate_confirmation_scenario_b(self):
        """Validates Scenario B software request proposal, creation, and duplicate confirmation suppression."""
        history = []
        r1 = self.client.post(
            "/api/kb/chat",
            json={"message": "I need Docker Desktop for development.", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()
        self.assertEqual(d1["intent"], "service_request")
        self.assertEqual(d1["action_proposed"]["catalog_item_id"], "cat-103")
        history.append({"role": "user", "content": "I need Docker Desktop for development."})
        history.append({"role": "assistant", "content": d1["message"]})

        # Confirm once
        r2 = self.client.post(
            "/api/kb/chat",
            json={"message": "Yes, confirm.", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertIsNotNone(d2["action_result"])
        req_id = d2["action_result"]["record_id"]
        self.assertTrue(req_id.startswith("REQ-"))
        history.append({"role": "user", "content": "Yes, confirm."})
        history.append({"role": "assistant", "content": d2["message"]})

        # Confirm second time (duplicate protection)
        r3 = self.client.post(
            "/api/kb/chat",
            json={"message": "Yes, confirm.", "history": history},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(r3.status_code, 200)
        d3 = r3.json()
        self.assertEqual(d3["intent"], "confirm_without_proposal")
        self.assertEqual(d3["generation_mode"], "already_confirmed")
        self.assertIsNone(d3["action_result"])
        self.assertIn(req_id, d3["message"])

    def test_ticket_status_access_control_scenario_c(self):
        """Validates access control: Employee cannot inspect tickets of other users, but Support Agent can."""
        # Employee Alex Morgan queries INC-1001 (DevOps Engineering)
        r_emp = self.client.post(
            "/api/kb/chat",
            json={"message": "What is the status of INC-1001?", "history": []},
            headers={"X-User-Name": "Alex Morgan", "X-User-Role": "Employee"},
        )
        self.assertEqual(r_emp.status_code, 200)
        d_emp = r_emp.json()
        self.assertEqual(d_emp["generation_mode"], "status_lookup_restricted")
        self.assertIn("Access Restricted", d_emp["message"])

        # Support Agent Sarah Chen queries INC-1001 (Assigned to her)
        r_agent = self.client.post(
            "/api/kb/chat",
            json={"message": "What is the status of INC-1001?", "history": []},
            headers={"X-User-Name": "Sarah Chen", "X-User-Role": "Support Agent"},
        )
        self.assertEqual(r_agent.status_code, 200)
        d_agent = r_agent.json()
        self.assertEqual(d_agent["generation_mode"], "status_lookup_detail")
        self.assertIn("INC-1001", d_agent["message"])
        self.assertIn("DevOps Engineering", d_agent["message"])

    def test_knowledge_search_and_no_match_scenario_d(self):
        """Validates grounded search for IT questions and clean no-match without hallucination for unrelated questions."""
        # 1. Grounded IT query
        r1 = self.client.post("/api/kb/chat", json={"message": "How do I configure office Wi-Fi?", "history": []})
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()
        self.assertTrue(d1["has_answer"])
        self.assertEqual(d1["matched_articles"][0]["id"], "kb-105")

        # 2. Unrelated query
        r2 = self.client.post("/api/kb/chat", json={"message": "What is the capital of France?", "history": []})
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertFalse(d2["has_answer"])
        self.assertEqual(d2["generation_mode"], "no_match")
        self.assertEqual(d2["matched_articles"], [])


if __name__ == "__main__":
    unittest.main()


