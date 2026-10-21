"""KB retrieval + grounded LLM tests. No MongoDB. No .env secrets."""

import os
import unittest
from unittest.mock import patch

os.environ["HELPWISE_CHROMA_DIR"] = ":memory:"
os.environ["HELPWISE_LLM_ENABLED"] = "1"

import rag
from rag import answer_question_from_dicts


_SAMPLE_ARTICLES = [
    {
        "id": "kb-101",
        "title": "Troubleshooting Cisco AnyConnect VPN Certificate Errors",
        "category": "Network",
        "read_time": "3 min",
        "excerpt": "Steps to resolve certificate validation failure when authenticating to the corporate VPN.",
        "content": "Install the company root CA and restart Cisco AnyConnect Secure Client.",
        "tags": ["VPN", "AnyConnect"],
        "updated_at": "2026-10-18T10:00:00Z",
    },
    {
        "id": "kb-102",
        "title": "Requesting and Activating JetBrains / IDE Developer Licenses",
        "category": "Access",
        "read_time": "2 min",
        "excerpt": "How new joiners obtain IntelliJ, PyCharm, or WebStorm seats.",
        "content": "Submit an Access ticket titled JetBrains Developer License Request.",
        "tags": ["License", "JetBrains", "IDE"],
        "updated_at": "2026-10-15T14:30:00Z",
    },
    {
        "id": "kb-103",
        "title": "Resolving Microsoft Outlook 365 Startup Crash (Error 0xc0000005)",
        "category": "Software",
        "read_time": "4 min",
        "excerpt": "Fix Outlook 365 crashes after Windows updates.",
        "content": "Launch Outlook in Safe Mode, then disable add-ins.",
        "tags": ["Outlook", "Office365", "Crash", "Email"],
        "updated_at": "2026-10-17T09:15:00Z",
    },
    {
        "id": "kb-104",
        "title": "Self-Service Multi-Factor Authentication (MFA) Reset Procedure",
        "category": "Access",
        "read_time": "3 min",
        "excerpt": "Reset authenticator after a phone replacement.",
        "content": "Use the identity portal recovery page and scan a new QR code.",
        "tags": ["MFA", "Okta", "Authentication"],
        "updated_at": "2026-10-12T16:00:00Z",
    },
    {
        "id": "kb-105",
        "title": "Corporate 802.1X Wi-Fi Connection Guide",
        "category": "Hardware",
        "read_time": "2 min",
        "excerpt": "Configure WPA3-Enterprise 802.1X on laptops.",
        "content": "Select SSID HelpWise-Secure and use PEAP.",
        "tags": ["Wi-Fi", "Network"],
        "updated_at": "2026-10-10T11:45:00Z",
    },
]


def _assert_clean_user_answer(testcase, answer: str):
    lowered = answer.lower()
    for banned in (
        "llm used",
        "vector database",
        "chromadb",
        "minilm",
        "tf-idf",
        "embedding",
        "confidence",
        "retrieval_method",
    ):
        testcase.assertNotIn(banned, lowered)


class TestKnowledgeRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rag._chroma_client = None
        rag._chroma_collection = None
        rag._chroma_fp = None

    def setUp(self):
        self.llm_patch = patch("rag.kb_llm.generate_grounded_answer", return_value=None)
        self.llm_patch.start()

    def tearDown(self):
        self.llm_patch.stop()

    def _ask(self, question: str):
        return answer_question_from_dicts(question, _SAMPLE_ARTICLES)

    def test_wifi_retrieval_success(self):
        result = self._ask("I can't connect to office wifi")
        self.assertGreaterEqual(len(result.matched_articles), 1)
        self.assertEqual(result.matched_articles[0].id, "kb-105")
        self.assertFalse(result.llm_used)
        self.assertIn("HelpWise-Secure", result.answer)
        _assert_clean_user_answer(self, result.answer)

    def test_outlook_retrieval_success(self):
        result = self._ask("outlook keeps crashing")
        self.assertEqual(result.matched_articles[0].id, "kb-103")
        _assert_clean_user_answer(self, result.answer)

    def test_mfa_retrieval_success(self):
        result = self._ask("I lost my phone and can't log in")
        self.assertEqual(result.matched_articles[0].id, "kb-104")

    def test_vpn_retrieval_success(self):
        result = self._ask("vpn certificate from home")
        self.assertEqual(result.matched_articles[0].id, "kb-101")

    def test_software_installation_retrieval(self):
        result = self._ask("how do I get PyCharm installed on my laptop")
        self.assertEqual(result.matched_articles[0].id, "kb-102")

    def test_no_match_fallback_is_clean(self):
        result = self._ask("completely unrelated gardening query xyz")
        self.assertEqual(result.matched_articles, [])
        self.assertFalse(result.llm_used)
        self.assertEqual(result.generation_mode, "no_match")
        self.assertIn("create an incident ticket", result.answer.lower())
        _assert_clean_user_answer(self, result.answer)

    def test_grounded_llm_answer_uses_article(self):
        self.llm_patch.stop()
        with patch(
            "rag.kb_llm.generate_grounded_answer",
            return_value="1. Select the HelpWise-Secure Wi-Fi network.\n2. Use PEAP as described in the article.",
        ) as mocked:
            result = self._ask("I can't connect to office wifi")
        mocked.assert_called()
        self.assertTrue(result.llm_used)
        self.assertEqual(result.generation_mode, "flan_t5_small_grounded")
        self.assertIn("HelpWise-Secure", result.answer)
        self.assertIn("PEAP", result.answer)
        _assert_clean_user_answer(self, result.answer)

    def test_llm_failure_falls_back_without_claiming_llm(self):
        self.llm_patch.stop()
        with patch("rag.kb_llm.generate_grounded_answer", side_effect=RuntimeError("model failed")):
            result = self._ask("outlook keeps crashing")
        self.assertFalse(result.llm_used)
        self.assertEqual(result.generation_mode, "extractive_fallback")
        self.assertIn("Safe Mode", result.answer)
        _assert_clean_user_answer(self, result.answer)

    def test_grounding_rejects_repetitive_loop(self):
        from llm import _has_repeated_content, _is_grounded
        from schemas import KBAskHit

        hit = KBAskHit(
            id="kb-101",
            title="VPN Troubleshooting",
            category="Network",
            excerpt="VPN cert steps",
            content="Install root CA certificate and restart Cisco AnyConnect.",
            tags=["VPN"],
            score=0.9,
        )
        loop_text = "Step1: How to install a VPN. Step2: How to install a VPN. Step3: Install the root CA."
        self.assertTrue(_has_repeated_content(loop_text))
        self.assertFalse(_is_grounded(loop_text, [hit]))

    def test_grounding_rejects_foreign_tool_leakage(self):
        from llm import _is_grounded
        from schemas import KBAskHit

        # Outlook article should not allow AnyConnect or PyCharm
        hit = KBAskHit(
            id="kb-103",
            title="Outlook Crash",
            category="Software",
            excerpt="Outlook fix",
            content="Launch in safe mode and disable add-ins.",
            tags=["Outlook"],
            score=0.9,
        )
        leaked_text = "Launch Outlook in safe mode, then install Cisco AnyConnect and connect to VPN."
        self.assertFalse(_is_grounded(leaked_text, [hit]))


class TestRealFlanT5Generation(unittest.TestCase):
    """Loads google/flan-t5-small once. Tests real generation and safe fallback."""

    @classmethod
    def setUpClass(cls):
        rag._chroma_client = None
        rag._chroma_collection = None
        rag._chroma_fp = None

    def test_flan_t5_small_returns_grounded_wifi_answer(self):
        result = answer_question_from_dicts("I can't connect to office wifi", _SAMPLE_ARTICLES)
        self.assertEqual(result.matched_articles[0].id, "kb-105")
        self.assertTrue(result.llm_used, "flan-t5-small did not produce a grounded answer")
        self.assertEqual(result.generation_mode, "flan_t5_small_grounded")
        lowered = result.answer.lower()
        self.assertTrue(
            "wifi" in lowered or "wi-fi" in lowered or "peap" in lowered or "helpwise-secure" in lowered or "ssid" in lowered,
            result.answer,
        )
        _assert_clean_user_answer(self, result.answer)

    def test_flan_t5_small_vpn_grounded_or_safe_fallback(self):
        result = answer_question_from_dicts("I have a VPN certificate error from home", _SAMPLE_ARTICLES)
        self.assertEqual(result.matched_articles[0].id, "kb-101")
        # Must be either flan_t5_small_grounded or extractive_fallback
        self.assertIn(result.generation_mode, ["flan_t5_small_grounded", "extractive_fallback"])
        lowered = result.answer.lower()
        # Must contain legitimate VPN steps
        self.assertTrue("anyconnect" in lowered or "certificate" in lowered or "root ca" in lowered, result.answer)
        # Must NOT contain repeated step loops
        self.assertNotIn("step1: how to install a vpn on your computer. step2: how to install", lowered)
        _assert_clean_user_answer(self, result.answer)


if __name__ == "__main__":
    unittest.main()
