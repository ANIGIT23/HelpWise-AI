"""
All-Rounder ITSM Assistant — Conversational, Context-Aware Intent & Action Engine.

Capabilities:
1. Natural conversation: greetings, thanks/gratitude, closings, conversational follow-ups.
2. Context awareness: understands "I tried that, but it still doesn't work", "what next?",
   "explain in simple terms", preserving topic context without robotic repetition.
3. Stateful troubleshooting: tracks reported issue, steps attempted, failure counts, and progresses
   from Step 1 (initial advice) -> Step 2 (isolation) -> Step 3 (diagnostics/settings) -> Step 4 (escalation).
4. Confirmation guardrails & duplicate protection: validates pending proposals and prevents duplicate tickets/requests.
5. Access-controlled ticket status lookup: allows employees to view only their own tickets, while agents/admins inspect full details.
6. All-rounder actions: service request submission, incident intake with troubleshooting context, self-heal diagnostics.
7. Grounded knowledge retrieval: MiniLM + ChromaDB RAG with citation linking and repetition suppression.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional, Tuple

import database
import diagnostics
import rag
from schemas import (
    ChatMessage,
    ChatResponse,
    KBAskHit,
    KBArticle,
    TicketCreate,
    TicketCategory,
    TicketPriority,
    ServiceRequestCreate,
    RequestCategory,
)

# ── Conversational Pattern RegExes ───────────────────────────────────────────

_GREETING_PATTERNS = [
    r"^(hi|hello|hey|good\s*(morning|afternoon|evening|day)|howdy|greetings)(\s+(there|assistant|bot|team|all|helpwise))?[\s!.]*$",
    r"^(what\s*can\s*you\s*do|who\s*are\s*you|what\s*are\s*your\s*capabilities|help\s*me|how\s*can\s*you\s*help)[\s?.]*$",
]

_GRATITUDE_PATTERNS = [
    r"^(thanks?|thank\s*you|thx|appreciate\s*it|great\s*thanks|awesome\s*thanks)[\s.!]*$",
    r"\b(thanks?|thank\s*you)\s*,?\s*(that\s*helped|that\s*works?|that\s*fixed\s*it|very\s*much|a\s*lot|so\s*much)?\b",
    r"^that\s*(helped|worked|fixed\s*it)[\s.!]*$",
]

def _is_affirmative_confirmation(msg: str) -> bool:
    m = msg.strip().lower()
    if any(q in m for q in ["status", "is my", "if my", "are my", "can you check", "open an incident", "create a ticket"]):
        return False
    if re.search(r"^\s*(yes\b|confirm\b|sure\b|proceed\b|go\s*ahead\b|please\s*(confirm|create|submit|proceed))", m):
        return True
    if re.search(r"\b(confirm\s*(it|this|creation|submission|request|please)?|yes,?\s*(confirm|please|proceed)?)\b", m):
        return True
    return False


_STATUS_PATTERNS = [
    r"\bstatus\s+of\s+(my\s+)?tickets?\b",
    r"\bmy\s+open\s+tickets?\b",
    r"\bcheck\s+(my\s+)?tickets?\b",
    r"\bwhere\s+is\s+my\s+ticket\b",
    r"\btrack\s+(my\s+)?tickets?\b",
    r"\b(status\s+of|tell\s+me\s+about|info\s+on|details?\s+(for|of)|who\s+is\s+assigned\s+to|what\s+is\s+the\s+status\s+of)\s+(ticket\s+)?(inc-\d+)\b",
    r"\b(inc-\d+)\s+status\b",
    r"^inc-\d+$",
]

_FAILED_ATTEMPT_PATTERNS = [
    r"\btried\s+(that|this|it|those)\b",
    r"\b(still|doesn'?t|does\s+not|didn'?t|did\s+not)\s+work\b",
    r"\bstill\s+(having\s+(the\s+)?issue|disconnecting|failing|broken|crashing|drops?|dropping|not\s+working)\b",
    r"\bno\s+luck\b",
    r"\b(didn'?t|did\s+not|doesn'?t|does\s+not)\s+(help|fix|solve)\b",
    r"\bhasn'?t\s+(fixed|helped|solved)\b",
    r"\bthat\s+(failed|didn'?t\s+help|didn'?t\s+work)\b",
    r"\bdidn'?t\s+help\s+either\b",
    r"\balready\s+(tried|did\s+that)\b",
    r"\bnot\s+helping\b",
    r"\bthat\s+didn'?t\s+help\s+either\b",
]

_NEXT_STEPS_PATTERNS = [
    r"what\s*(should|can|do)\s*i\s*do\s*next",
    r"what('?s|\s*is)\s*next",
    r"^what\s*next[\s?.]*$",
    r"^next\s*steps?[\s?.]*$",
    r"^and\s*then[\s?.]*$",
    r"where\s*do\s*i\s*go\s*from\s*here",
    r"what\s*is\s*the\s*next\s*step",
]

_SIMPLIFY_PATTERNS = [
    r"\bexplain\s+(it|that|this)\s+simply\b",
    r"\bexplain\s+(that|this|it)?\s*(in\s+)?(simple\s+terms|plain\s+english|plain\s+words|plain\s+language)\b",
    r"\bcan\s+you\s+explain\s+(it|that|this)?\s*simply\b",
    r"\bcan\s+you\s+simplify\b",
    r"\bsimplify\s+(this|that|it|steps?|instructions?)\b",
    r"\bbreak\s+(it|this|that)\s+down\b",
    r"\bwhat\s+does\s+that\s+mean\b",
    r"\btoo\s+technical\b",
    r"\bsimpler\s+terms\b",
    r"\bin\s+(simple\s+terms|plain\s+english|plain\s+language)\b",
    r"\bi\s+don'?t\s+understand\b",
    r"\bmake\s+it\s+simpler\b",
]

_INCIDENT_INTAKE_PATTERNS = [
    r"\b(can|could|please|would)\s+(you\s+)?(open|create|log|raise|submit)\s+(an?\s+)?(incident|ticket)\b",
    r"\b(open|create|log|raise|submit)\s+(an?\s+)?(incident|ticket)\b",
    r"\bopen\s+(a\s+)?ticket\s+for\b",
    r"\bfile\s+(an?\s+)?(incident|ticket)\b",
]

_REQUEST_KEYWORDS = {
    "cat-101": ["vscode", "vs code", "visual studio code"],
    "cat-102": ["jetbrains", "pycharm", "intellij", "webstorm", "goland", "ide license"],
    "cat-103": ["docker", "docker desktop", "container"],
    "cat-104": ["postman", "api testing"],
    "cat-105": ["cloud sandbox", "aws", "gcp", "azure", "cloud project"],
    "cat-106": ["vpn profile", "vpn access", "remote access profile"],
    "cat-107": ["monitor", "4k monitor", "screen", "dell monitor"],
    "cat-108": ["yubikey", "fido", "security key", "hardware key"],
}


def _match_catalog_item(query: str) -> Optional[Dict[str, Any]]:
    lowered = query.lower()
    for cat_id, terms in _REQUEST_KEYWORDS.items():
        if any(term in lowered for term in terms):
            for item in database.CATALOG_ITEMS:
                if item.id == cat_id:
                    return {
                        "id": item.id,
                        "name": item.name,
                        "category": item.category.value if hasattr(item.category, "value") else str(item.category),
                        "description": item.description,
                        "requires_approval": item.requires_approval,
                    }
    return None


def _extract_ticket_number(text: str) -> Optional[str]:
    m = re.search(r"\b(INC-\d+)\b", text, re.IGNORECASE)
    return m.group(1).upper() if m else None


def _has_pending_proposal(history: List[ChatMessage]) -> Optional[str]:
    """
    Checks the last assistant message in history to determine if an unconfirmed
    action proposal is pending. Returns 'service_request', 'ticket', or None.
    """
    if not history:
        return None

    last_assistant_turn = None
    for turn in reversed(history):
        if turn.role == "assistant":
            last_assistant_turn = turn
            break

    if not last_assistant_turn:
        return None

    content_lower = last_assistant_turn.content.lower()

    # If already confirmed or completed in this message, no proposal is pending
    if (
        "successfully submitted" in content_lower
        or "successfully created" in content_lower
        or "record created" in content_lower
    ):
        return None

    if (
        "proposed service request" in content_lower
        or "confirm submission of this request" in content_lower
        or "service request proposal" in content_lower
    ):
        return "service_request"

    if (
        "incident ticket proposal" in content_lower
        or "proposed incident ticket" in content_lower
        or "confirm creation of this ticket" in content_lower
        or "open this ticket? reply" in content_lower
    ):
        return "ticket"

    return None


def _get_recently_completed_action(history: List[ChatMessage]) -> Optional[Tuple[str, str]]:
    """
    Checks if a ticket or service request was already created in this conversation.
    Returns (record_type, record_id) if found in recent assistant messages.
    """
    for turn in reversed(history):
        if turn.role == "assistant":
            m_ticket = re.search(r"Ticket Number.*?(INC-\d+)", turn.content, re.IGNORECASE)
            if m_ticket:
                return ("incident ticket", m_ticket.group(1).upper())
            m_req = re.search(r"Request Number.*?(REQ-\d+)", turn.content, re.IGNORECASE)
            if m_req:
                return ("service request", m_req.group(1).upper())
            if "record created" in turn.content.lower():
                m_rec = re.search(r"(INC-\d+|REQ-\d+)", turn.content, re.IGNORECASE)
                if m_rec:
                    return ("record", m_rec.group(1).upper())
    return None


def _detect_context_topic(history: List[ChatMessage], current_message: str) -> str:
    """Extracts the active IT troubleshooting topic from conversation context."""
    low_curr = current_message.lower()
    if any(k in low_curr for k in ["vpn", "anyconnect", "cisco", "tunnel", "certificate 0x800b0109"]):
        return "vpn"
    if any(k in low_curr for k in ["outlook", "0xc0000005", "email crash", "office 365", "safe mode"]):
        return "outlook"
    if any(k in low_curr for k in ["mfa", "okta", "authenticator", "lost phone", "qr code", "two-factor"]):
        return "mfa"
    if any(k in low_curr for k in ["wifi", "wi-fi", "wireless", "ssid", "helpwise-secure", "peap"]):
        return "wifi"
    if any(k in low_curr for k in ["jetbrains", "intellij", "pycharm", "webstorm", "ide license"]):
        return "jetbrains"

    # Check user turns in history first (user questions define topic intent)
    for turn in reversed(history):
        if turn.role == "user":
            content = turn.content.lower()
            if any(k in content for k in ["wifi", "wi-fi", "wireless", "ssid", "helpwise-secure", "peap"]):
                return "wifi"
            if any(k in content for k in ["vpn", "anyconnect", "cisco", "tunnel", "0x800b0109"]):
                return "vpn"
            if any(k in content for k in ["outlook", "0xc0000005", "email crash", "office 365", "safe mode"]):
                return "outlook"
            if any(k in content for k in ["mfa", "okta", "authenticator", "lost phone", "qr code", "two-factor"]):
                return "mfa"
            if any(k in content for k in ["jetbrains", "intellij", "pycharm", "webstorm", "ide license"]):
                return "jetbrains"

    # Fall back to assistant turns if user turn was very brief
    for turn in reversed(history):
        content = turn.content.lower()
        if any(k in content for k in ["helpwise-secure", "802.1x", "wi-fi"]):
            return "wifi"
        if any(k in content for k in ["anyconnect", "cisco", "0x800b0109"]):
            return "vpn"
        if any(k in content for k in ["outlook", "0xc0000005", "safe mode"]):
            return "outlook"
        if any(k in content for k in ["okta", "authenticator", "mfa reset"]):
            return "mfa"
        if any(k in content for k in ["jetbrains", "intellij", "pycharm", "webstorm"]):
            return "jetbrains"

    return "general"


def _analyze_troubleshooting_state(history: List[ChatMessage], topic: str) -> Dict[str, Any]:
    """
    Analyzes conversation history to determine:
    - Number of failed troubleshooting attempts reported by user for this topic
    - Last specific advice given (e.g. step_1_initial, step_2_isolation, step_3_advanced)
    """
    failure_count = 0
    last_advice = "step_1_initial"

    for turn in history:
        content_lower = turn.content.lower()
        if turn.role == "user":
            if any(re.search(pat, content_lower) for pat in _FAILED_ATTEMPT_PATTERNS):
                failure_count += 1
        elif turn.role == "assistant":
            if any(k in content_lower for k in ["hotspot", "isolate your network", "quick repair", "clean mail profile", "time correction", "random hardware addresses"]):
                last_advice = "step_2_isolation"
            elif any(k in content_lower for k in ["passthrough", "router settings", "event viewer", "self-heal", "diagnostic"]):
                last_advice = "step_3_advanced"
            elif any(k in content_lower for k in ["certmgr", "safe mode", "recovery", "peap"]):
                last_advice = "step_1_initial"

    return {
        "failure_count": failure_count,
        "last_advice": last_advice,
    }


def _get_article_for_topic(topic: str, articles: List[KBArticle]) -> Optional[KBAskHit]:
    topic_map = {
        "vpn": "kb-101",
        "jetbrains": "kb-102",
        "outlook": "kb-103",
        "mfa": "kb-104",
        "wifi": "kb-105",
    }
    art_id = topic_map.get(topic)
    if not art_id:
        return None
    for a in articles:
        if a.id == art_id:
            return KBAskHit(
                id=a.id,
                title=a.title,
                category=a.category,
                excerpt=a.excerpt,
                content=a.content,
                tags=a.tags,
                score=0.95,
            )
    return None


def _classify_intent(message: str, history: List[ChatMessage]) -> str:
    msg = message.strip().lower()

    # 1. Greetings
    if any(re.search(pat, msg) for pat in _GREETING_PATTERNS):
        return "greeting"

    # 2. Gratitude / Closings
    if any(re.search(pat, msg) for pat in _GRATITUDE_PATTERNS):
        return "gratitude"

    # 3. Explicit confirmations
    if _is_affirmative_confirmation(msg):
        pending = _has_pending_proposal(history)
        if pending == "ticket":
            return "confirm_ticket"
        elif pending == "service_request":
            return "confirm_service_request"
        else:
            return "confirm_without_proposal"

    # 4. Context Follow-up: Solution Failed / Still Not Working
    if any(re.search(pat, msg) for pat in _FAILED_ATTEMPT_PATTERNS):
        return "troubleshooting_failed"

    # 5. Context Follow-up: Explain Simply
    if any(re.search(pat, msg) for pat in _SIMPLIFY_PATTERNS):
        return "explain_simply"

    # 6. Context Follow-up: What next?
    if any(re.search(pat, msg) for pat in _NEXT_STEPS_PATTERNS):
        return "what_next"

    # 7. Explicit Incident Creation Intent
    if any(re.search(pat, msg) for pat in _INCIDENT_INTAKE_PATTERNS):
        return "incident_intake"

    # 8. Ticket Status Lookup
    if any(re.search(pat, msg) for pat in _STATUS_PATTERNS):
        return "ticket_status"

    # 9. Diagnostics Intent
    if any(word in msg for word in ["run diagnostic", "check network", "test dns", "check disk", "self-heal", "system health"]):
        return "diagnostic"

    # 10. Service Request Intent
    if (
        "request" in msg
        or "need a license" in msg
        or "need access" in msg
        or "order a" in msg
        or "give me" in msg
        or _match_catalog_item(msg) is not None
    ) and not any(k in msg for k in ["how to", "steps to", "troubleshoot", "why", "error"]):
        if _match_catalog_item(msg) is not None:
            return "service_request"

    # 11. Default to Knowledge Search (RAG)
    return "knowledge_search"


async def handle_conversational_turn(
    message: str,
    history: List[ChatMessage],
    user_name: str = "Alex Morgan",
    user_role: str = "Employee",
) -> ChatResponse:
    """Processes incoming chat turn through the intent router and returns structured response."""
    intent = _classify_intent(message, history)
    articles = await database.get_kb_articles()

    # ── 1. Greeting ─────────────────────────────────────────────────────────────
    if intent == "greeting":
        greeting_text = (
            f"Hello {user_name}! 👋 I am your HelpWise AI IT Support Assistant.\n\n"
            "I'm here to help you solve technical issues, request software and access, or manage support tickets:\n"
            "• **Troubleshooting & Knowledge**: Ask any IT question (VPN, Wi-Fi, Outlook, MFA).\n"
            "• **Software & Service Requests**: Request tools like Docker Desktop, VS Code, or JetBrains.\n"
            "• **Incident Management**: Describe an issue to log a ticket with IT Support.\n"
            "• **Ticket Tracking**: Check the status of your submitted and assigned tickets.\n"
            "• **Diagnostics**: Run safe self-healing checks for network and system health.\n\n"
            "How can I assist you right now?"
        )
        return ChatResponse(
            message=greeting_text,
            matched_articles=[],
            generation_mode="greeting",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="greeting",
        )

    # ── 2. Gratitude / Closing ──────────────────────────────────────────────────
    if intent == "gratitude":
        gratitude_text = (
            f"You're very welcome, {user_name}! 😊 Glad I could help.\n\n"
            "If you need anything else with your IT setup, software licenses, or tickets, "
            "just let me know. Have a wonderful day!"
        )
        return ChatResponse(
            message=gratitude_text,
            matched_articles=[],
            generation_mode="gratitude",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="gratitude",
        )

    # ── 3. Confirmation Without Proposal / Duplicate Confirmation Guardrail ────
    if intent == "confirm_without_proposal":
        recent_done = _get_recently_completed_action(history)
        if recent_done:
            rec_type, rec_id = recent_done
            msg_text = (
                f"✅ Your {rec_type} (**{rec_id}**) has already been successfully confirmed and submitted!\n\n"
                f"No duplicate record was created. You can track this under the corresponding tab in the platform.\n"
                f"Is there anything else I can assist you with?"
            )
        else:
            msg_text = (
                "There is currently no pending ticket or service request to confirm.\n\n"
                "If you'd like to request software (such as Docker Desktop, VS Code, or JetBrains) "
                "or report an IT problem, tell me what you need and I'll prepare a request for you!"
            )
        return ChatResponse(
            message=msg_text,
            matched_articles=[],
            generation_mode="already_confirmed" if recent_done else "no_pending_proposal",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="confirm_without_proposal",
        )

    # ── 4. Solution Failed Follow-up (Stateful Troubleshooting) ─────────────────
    if intent == "troubleshooting_failed":
        topic = _detect_context_topic(history, message)
        state = _analyze_troubleshooting_state(history, topic)
        failure_count = state["failure_count"]
        hit = _get_article_for_topic(topic, articles)
        matched = [hit] if hit else []

        if topic == "vpn":
            if failure_count == 0:
                # 1st failure report: move to Step 2 Network Isolation & Conflicting Adapters
                failed_text = (
                    "I understand—sorry to hear restarting AnyConnect and checking the root certificate didn't resolve the disconnects.\n\n"
                    "Let's move to **Step 2: Network Isolation & Adapter Conflicts**:\n"
                    "• **Isolate your network**: Connect your laptop to your mobile phone's cellular hotspot for 5–10 minutes. "
                    "If AnyConnect stays connected without dropping, your home Wi-Fi router's firewall or SPI packet filter is dropping the tunnel.\n"
                    "• **Disable conflicting adapters**: Shut down personal VPNs (Tailscale, NordVPN, Proton) or Docker Desktop, "
                    "which frequently hijack corporate 10.x.x.x routing tables.\n\n"
                    "Let me know if testing on mobile hotspot stabilizes the connection, or if you'd like me to explain any of these steps simply!"
                )
            elif failure_count == 1:
                # 2nd failure report: move to Step 3 Router settings & Diagnostics
                failed_text = (
                    "Thank you for testing that. Since testing on hotspot and closing conflicting adapters didn't stop the disconnects, "
                    "the issue is likely caused by router gateway filtering or local route table conflicts.\n\n"
                    "Here is **Step 3: Advanced Network Checks**:\n"
                    "• **Router Passthrough**: Check your home router admin settings and ensure **IPsec Passthrough** and **PPTP/L2TP Passthrough** are enabled.\n"
                    "• **Automated Diagnostics**: We can run an automated **Self-Heal Network Diagnostic** right now to test gateway latency, DNS reachability, and MTU packet size.\n\n"
                    "Would you like me to run network diagnostics now, or should I open an incident ticket for our IT Network Engineering team?"
                )
            else:
                # 3+ failures: Escalate
                failed_text = (
                    "I see that the disconnects persist despite restarting AnyConnect, checking root certificates, testing on mobile hotspot, "
                    "and reviewing adapter settings.\n\n"
                    "Because all supported local troubleshooting steps have failed, this indicates an issue with your corporate VPN profile, "
                    "gateway authentication, or gateway IP routing on the server side.\n\n"
                    "I recommend escalating directly to our **IT Network Operations** team. Would you like me to open an incident ticket for you now?"
                )
        elif topic == "outlook":
            if failure_count == 0:
                failed_text = (
                    "Sorry to hear Safe Mode didn't resolve the Outlook crashes.\n\n"
                    "Let's move to **Step 2: Repair & Clean Profile**:\n"
                    "• **Quick Repair Microsoft 365**: Go to Windows Settings > Installed Apps > Microsoft 365 > Modify, then choose **Quick Repair**.\n"
                    "• **Test with a clean mail profile**: Open Windows Control Panel > Mail > Show Profiles > Add, and create a test profile to see if your local `.ost` data file is corrupted.\n\n"
                    "Let me know if Quick Repair helps, or if you'd like me to explain how to create a test profile!"
                )
            else:
                failed_text = (
                    "Since both Safe Mode and Quick Repair were unable to stop the crash (Error 0xc0000005), "
                    "this usually indicates corrupted Office runtime binaries or an incompatible Windows graphics driver.\n\n"
                    "I recommend opening an incident ticket so our Desktop Support specialists can inspect the Windows Event Viewer crash dump and repair your installation.\n\n"
                    "Would you like me to open that ticket for you right now?"
                )
        elif topic == "mfa":
            failed_text = (
                "Understood. If the self-service recovery page didn't let you re-register your authenticator app, "
                "your account credentials are likely locked for your security.\n\n"
                "Because self-service options are exhausted, an IT Support engineer must verify your identity "
                "and generate an emergency one-time bypass code.\n\n"
                "Would you like me to open an urgent **Access & Permissions** incident ticket for our Identity Support team?"
            )
        elif topic == "wifi":
            if failure_count == 0:
                failed_text = (
                    "Sorry to hear you still cannot connect to HelpWise-Secure Wi-Fi.\n\n"
                    "Let's try **Step 2: Forget Network & MAC Settings**:\n"
                    "• **Forget Network**: Go to Wi-Fi Settings > Manage Known Networks > HelpWise-Secure > **Forget**, then reconnect and re-enter your credentials.\n"
                    "• **Turn off MAC Randomization**: Ensure 'Random Hardware Addresses' is turned off for the network, as corporate RADIUS servers require fixed hardware addresses.\n\n"
                    "Let me know if reconnecting with fixed MAC address works, or if you'd like me to run network diagnostics!"
                )
            else:
                failed_text = (
                    "Since forgetting the network and disabling MAC randomization didn't resolve the issue, "
                    "your laptop's wireless certificate or 802.1X supplicant configuration may need re-provisioning.\n\n"
                    "Would you like me to open an incident ticket for our Network Infrastructure team to inspect your connection?"
                )
        else:
            failed_text = (
                "I'm sorry that didn't resolve the issue. Since the standard troubleshooting steps didn't work, let's take a closer look.\n\n"
                "We can:\n"
                "1. Run **Self-Heal Diagnostics** to check your local connectivity and system health.\n"
                "2. Open an **Incident Ticket** so an IT specialist can review your logs and help you directly.\n\n"
                "Which would you prefer to do?"
            )

        return ChatResponse(
            message=failed_text,
            matched_articles=matched,
            generation_mode="troubleshooting_escalation",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="troubleshooting_failed",
        )

    # ── 5. Explain Simply Follow-up (Context-Aware Simplification) ─────────────
    if intent == "explain_simply":
        topic = _detect_context_topic(history, message)
        state = _analyze_troubleshooting_state(history, topic)
        last_advice = state["last_advice"]
        hit = _get_article_for_topic(topic, articles)
        matched = [hit] if hit else []

        if topic == "vpn":
            if last_advice == "step_2_isolation":
                simple_text = (
                    "Here is what those checks mean in simple terms:\n\n"
                    "• **Why test on your phone's personal hotspot**:\n"
                    "  Think of your home Wi-Fi like a security gate. Sometimes home routers have strict firewalls that block company work tunnels. "
                    "  When you connect to your phone's cellular hotspot, you bypass your home router entirely. If the VPN works on your phone's data, "
                    "  it proves your laptop and work account are completely fine, and your home router is the one dropping the connection.\n\n"
                    "• **Why close Docker or personal VPNs**:\n"
                    "  Apps like Docker Desktop or personal VPNs create their own hidden mini-networks inside your computer. "
                    "  Sometimes they accidentally use the exact same private network addresses (10.x.x.x) that our company uses, "
                    "  causing work files to get sent to the wrong place.\n\n"
                    "Does that make more sense? Feel free to give it a try, or let me know if you would like me to open a ticket for IT Support!"
                )
            else:
                simple_text = (
                    "Here is how the VPN works in simple terms:\n\n"
                    "1. **A Private Tunnel**: The VPN connects your laptop to the office network like an invisible private cable.\n"
                    "2. **Security ID Badge**: Before letting you into the office network, the VPN checks a digital certificate (like an ID badge) stored on your laptop. If it's missing or out of date, it denies access.\n"
                    "3. **Quick Fix**: Updating the company root certificate and reconnecting usually fixes the issue immediately.\n\n"
                    "Would you like me to guide you through updating the certificate, or should I open a support ticket for hands-on help?"
                )
        elif topic == "outlook":
            simple_text = (
                "Here it is in simple terms:\n\n"
                "1. **Add-ins are extra plugins**: Tools like Zoom, Teams, or antivirus tools install little plugins inside Outlook.\n"
                "2. **Safe Mode turns plugins off**: Starting Outlook in Safe Mode runs it without plugins, so we can see if a plugin caused the crash.\n"
                "3. **Quick Repair fixes files**: Windows can scan and replace any damaged Office program files automatically.\n\n"
                "Would you like me to open an IT ticket if you'd like someone to help you step by step?"
            )
        elif topic == "mfa":
            simple_text = (
                "Here it is in simple terms:\n\n"
                "1. **MFA is a two-step lock**: Your password is the first key, and the app on your phone is the second key.\n"
                "2. **New phone, new code**: When you get a new phone, the app doesn't have your company's secret code yet.\n"
                "3. **Resetting it**: You need a temporary pass from IT to prove it's you, and then you scan a new QR code with your phone camera.\n\n"
                "Would you like me to submit an access ticket for you?"
            )
        elif topic == "wifi":
            simple_text = (
                "Here it is in simple terms:\n\n"
                "1. Look for the **HelpWise-Secure** network name on your laptop or phone.\n"
                "2. Sign in using your standard corporate email and password.\n"
                "3. If your screen asks you to trust a certificate, click **Accept** or **Trust**.\n"
                "4. Make sure your Wi-Fi settings aren't using a randomized MAC address, as the office network needs to recognize your laptop.\n\n"
                "Would you like me to help you test the connection or run network diagnostics?"
            )
        else:
            simple_text = (
                "In simple terms: we want to verify the basics first—make sure your apps are updated, restart the affected program, "
                "and check that your network connection is steady. If those don't work, having IT check your logs is the safest way to fix it.\n\n"
                "Shall I open a support ticket for you?"
            )

        return ChatResponse(
            message=simple_text,
            matched_articles=matched,
            generation_mode="simplified_explanation",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="explain_simply",
        )

    # ── 6. What Next Follow-up ─────────────────────────────────────────────────
    if intent == "what_next":
        topic = _detect_context_topic(history, message)
        hit = _get_article_for_topic(topic, articles)
        matched = [hit] if hit else []

        if topic == "vpn":
            next_text = (
                "Here is the recommended next course of action:\n\n"
                "1. **Test on your phone's mobile hotspot**: This immediately proves whether the issue is with your home router or the corporate gateway.\n"
                "2. **Run Diagnostics**: We can execute a live network health check to test DNS resolution and gateway latency.\n"
                "3. **Log an Incident Ticket**: If the problem persists, I can log a ticket directly for our Network Operations team so an engineer can inspect your VPN disconnect logs.\n\n"
                "Would you like me to run network diagnostics now, or should I open an incident ticket for you?"
            )
        elif topic == "outlook":
            next_text = (
                "Here is what you should do next:\n\n"
                "1. Run the **Quick Repair** utility for Microsoft 365 in Windows Settings.\n"
                "2. If Outlook still crashes, let's open an incident ticket so Desktop Support can inspect the Windows Event Viewer crash log (Error 0xc0000005) with you.\n\n"
                "Shall I open an incident ticket for you now?"
            )
        elif topic == "mfa":
            next_text = (
                "The best next step is to log an urgent **Access & Permissions** ticket.\n\n"
                "An IT support engineer will verify your identity and send you a temporary one-time access pass so you can scan a new QR code on your phone.\n\n"
                "Would you like me to open that ticket now?"
            )
        else:
            next_text = (
                "Here are your best options for next steps:\n\n"
                "1. **Run Self-Heal Diagnostics**: Check your system connectivity and network status.\n"
                "2. **Open an Incident Ticket**: Log an incident with IT Support so an agent can assist you directly.\n\n"
                "Let me know which option you would prefer!"
            )

        return ChatResponse(
            message=next_text,
            matched_articles=matched,
            generation_mode="next_steps_guidance",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="what_next",
        )

    # ── 7. Explicit Incident Intake Proposal ──────────────────────────────────
    if intent == "incident_intake":
        topic = _detect_context_topic(history, message)
        state = _analyze_troubleshooting_state(history, topic)

        if topic == "vpn":
            title = "Cisco AnyConnect VPN Disconnections"
            category = TicketCategory.NETWORK
            steps_tried = ["restarted AnyConnect and checked root certificate"]
            if state["failure_count"] >= 1:
                steps_tried.append("tested network isolation on mobile hotspot and checked conflicting adapters")
            summary_steps = ", ".join(steps_tried)
            description = (
                f"Incident logged via HelpWise AI Assistant.\n\n"
                f"Reported Issue: User experiences intermittent AnyConnect VPN tunnel disconnects.\n"
                f"Troubleshooting Attempted: User completed {summary_steps} without resolution.\n"
                f"Requester: {user_name}\n"
                f"Escalation Reason: Local troubleshooting exhausted; requires Network Engineering log inspection."
            )
        elif topic == "outlook":
            title = "Microsoft Outlook 365 Startup Crash (0xc0000005)"
            category = TicketCategory.SOFTWARE
            description = (
                f"Incident logged via HelpWise AI Assistant.\n\n"
                f"Reported Issue: Outlook crashes on startup.\n"
                f"Troubleshooting Attempted: Tested Safe Mode and Office repair.\n"
                f"Requester: {user_name}"
            )
        elif topic == "mfa":
            title = "MFA Authenticator Reset Assistance"
            category = TicketCategory.ACCESS
            description = (
                f"Incident logged via HelpWise AI Assistant.\n\n"
                f"Reported Issue: User cannot register replacement phone for corporate MFA.\n"
                f"Requester: {user_name}\n"
                f"Action Required: Identity Support verification and temporary bypass code generation."
            )
        elif topic == "wifi":
            title = "HelpWise-Secure Wi-Fi Connection Failure"
            category = TicketCategory.NETWORK
            description = (
                f"Incident logged via HelpWise AI Assistant.\n\n"
                f"Reported Issue: Device fails to authenticate to HelpWise-Secure 802.1X SSID.\n"
                f"Requester: {user_name}"
            )
        else:
            clean_text = re.sub(
                r"^(can|could|please|would)?\s*(you\s*)?(open|create|log|raise|submit)\s*(an?\s*)?(incident|ticket)\s*(for|about)?",
                "",
                message,
                flags=re.I,
            ).strip()
            title = clean_text[:100] if len(clean_text) >= 5 else "IT Support Incident logged via Chat"
            category = TicketCategory.SOFTWARE
            description = f"Incident submitted via chat: {message}\nRequester: {user_name}"

        proposal = {
            "type": "create_incident",
            "title": title,
            "category": category.value,
            "priority": TicketPriority.MEDIUM.value,
            "description": description,
            "requester": user_name,
            "details": {
                "title": title,
                "category": category.value,
                "priority": TicketPriority.MEDIUM.value,
                "description": description,
                "requester": user_name,
            },
        }

        context_summary = "User completed local troubleshooting without resolution."
        for line in description.splitlines():
            if "Troubleshooting Attempted:" in line:
                context_summary = line.replace("Troubleshooting Attempted:", "").strip()

        proposal_text = (
            f"I have prepared an **Incident Ticket Proposal**:\n\n"
            f"• **Title**: {title}\n"
            f"• **Category**: {category.value}\n"
            f"• **Priority**: Medium\n"
            f"• **Requester**: {user_name}\n"
            f"• **Troubleshooting Context**: {context_summary}\n\n"
            "Would you like me to open this ticket? Reply **\"Yes\"** or **\"Confirm\"** to log the incident."
        )

        return ChatResponse(
            message=proposal_text,
            matched_articles=[],
            generation_mode="ticket_intake_proposal",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="incident_intake",
            action_proposed=proposal,
        )

    # ── 8. Confirm Incident Creation Action ──────────────────────────────────
    if intent == "confirm_ticket":
        # Duplicate confirmation guardrail
        already_done = _get_recently_completed_action(history)
        if already_done and already_done[0] == "incident ticket":
            return ChatResponse(
                message=f"✅ Incident ticket **{already_done[1]}** has already been created! No duplicate ticket was created.",
                matched_articles=[],
                generation_mode="already_confirmed",
                llm_used=False,
                vector_database="none",
                has_answer=True,
                intent="confirm_without_proposal",
            )

        topic = _detect_context_topic(history, message)
        state = _analyze_troubleshooting_state(history, topic)

        clean_title = "Cisco AnyConnect VPN Disconnections" if topic == "vpn" else "IT Incident logged via Chat"
        cat = TicketCategory.NETWORK if topic in ["vpn", "wifi"] else TicketCategory.SOFTWARE

        # Look for custom proposal details in recent assistant message
        last_asst = next((h.content for h in reversed(history) if h.role == "assistant"), "")
        m_title = re.search(r"•\s*\*\*Title\*\*\s*:\s*([^\n]+)", last_asst)
        if m_title:
            clean_title = m_title.group(1).strip()
        m_cat = re.search(r"•\s*\*\*Category\*\*\s*:\s*([^\n]+)", last_asst)
        if m_cat:
            try:
                cat = TicketCategory(m_cat.group(1).strip())
            except Exception:
                pass

        try:
            ticket_payload = TicketCreate(
                title=clean_title,
                description=f"Incident confirmed and submitted through HelpWise AI Support Assistant.\n\nUser: {user_name}\nTopic: {topic}\nTroubleshooting failures logged: {state['failure_count']}",
                category=cat,
                priority=TicketPriority.MEDIUM,
                requester=user_name,
                assignee="Unassigned",
            )
            created_ticket = await database.create_ticket(ticket_payload)
            success_text = (
                f"🎫 **Incident Ticket Successfully Created!**\n\n"
                f"• **Ticket Number**: `{created_ticket.ticket_number}`\n"
                f"• **Title**: {created_ticket.title}\n"
                f"• **Status**: `{created_ticket.status}`\n"
                f"• **Priority**: `{created_ticket.priority}`\n"
                f"• **Requester**: {created_ticket.requester}\n\n"
                "Our IT Support team has been notified and will address your issue promptly. You can monitor progress under **My Tickets**."
            )
            return ChatResponse(
                message=success_text,
                matched_articles=[],
                generation_mode="ticket_created",
                llm_used=False,
                vector_database="none",
                has_answer=True,
                intent="incident_intake",
                action_result={
                    "success": True,
                    "type": "incident_created",
                    "record_type": "ticket",
                    "record_id": created_ticket.ticket_number,
                },
            )
        except Exception as exc:
            return ChatResponse(
                message=f"Failed to create incident: {str(exc)}",
                matched_articles=[],
                generation_mode="error",
                llm_used=False,
                vector_database="none",
                has_answer=False,
                intent="incident_intake",
            )

    # ── 9. Ticket Status Lookup with Role-Based Access Control ─────────────────
    if intent == "ticket_status":
        specific_id = _extract_ticket_number(message)
        if not specific_id:
            last_asst = next((h.content for h in reversed(history) if h.role == "assistant"), "")
            specific_id = _extract_ticket_number(last_asst)

        if specific_id:
            ticket = await database.get_ticket_by_id(specific_id)
            if not ticket:
                return ChatResponse(
                    message=f"Ticket `{specific_id}` was not found in our ITSM system.",
                    matched_articles=[],
                    generation_mode="status_lookup",
                    llm_used=False,
                    vector_database="none",
                    has_answer=False,
                    intent="ticket_status",
                )

            # Access Control: Employees can only view tickets they requested
            is_owner = user_name.lower() in ticket.requester.lower() or ticket.requester.lower() in user_name.lower()
            is_assignee = user_name.lower() in ticket.assignee.lower()
            is_staff = user_role in ["Support Agent", "Administrator"]

            if not (is_owner or is_assignee or is_staff):
                restricted_msg = (
                    f"🔒 **Access Restricted**: Ticket `{ticket.ticket_number}` is registered under **{ticket.requester}**.\n\n"
                    f"Under corporate data privacy and IT access control policy, employees may only view tickets they submitted. "
                    f"If you need updates regarding this incident, please contact {ticket.requester} or the IT Service Desk."
                )
                return ChatResponse(
                    message=restricted_msg,
                    matched_articles=[],
                    generation_mode="status_lookup_restricted",
                    llm_used=False,
                    vector_database="none",
                    has_answer=True,
                    intent="ticket_status",
                )

            # Authorized disclosure
            status_icon = "🟢" if ticket.status == "Open" else ("🟡" if ticket.status == "In Progress" else "✅")
            last_note = ticket.activity_history[-1].note if ticket.activity_history else "No activity notes recorded yet."
            detail_msg = (
                f"📋 **Ticket Details for {ticket.ticket_number}**:\n\n"
                f"• **Title**: {ticket.title}\n"
                f"• **Status**: {status_icon} `{ticket.status}`\n"
                f"• **Priority**: `{ticket.priority}`\n"
                f"• **Category**: `{ticket.category}`\n"
                f"• **Requester**: {ticket.requester}\n"
                f"• **Assignee**: {ticket.assignee}\n"
                f"• **Created**: {ticket.created_at[:10]}\n"
                f"• **Latest Activity**: {last_note}"
            )
            return ChatResponse(
                message=detail_msg,
                matched_articles=[],
                generation_mode="status_lookup_detail",
                llm_used=False,
                vector_database="none",
                has_answer=True,
                intent="ticket_status",
            )

        # General ticket list for user
        tickets = await database.get_all_tickets(
            requester=user_name if user_role == "Employee" else None,
            assignee=user_name if user_role == "Support Agent" else None,
        )
        if not tickets:
            status_text = (
                f"You currently have no open or assigned incident tickets under **{user_name}**.\n\n"
                "If you are experiencing an IT issue, describe it to me and I can help you open an incident ticket."
            )
        else:
            lines = [f"Here are the tickets registered for **{user_name}** ({len(tickets)} total):\n"]
            for t in tickets[:6]:
                status_icon = "🟢" if t.status == "Open" else ("🟡" if t.status == "In Progress" else "✅")
                lines.append(f"• **{t.ticket_number}**: {t.title}\n   Status: {status_icon} `{t.status}` | Priority: `{t.priority}` | Assignee: `{t.assignee}`")
            lines.append("\nYou can reply with **\"Status of INC-XXXX\"** for more details on any ticket.")
            status_text = "\n".join(lines)

        return ChatResponse(
            message=status_text,
            matched_articles=[],
            generation_mode="status_lookup",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="ticket_status",
        )

    # ── 10. Service Request Proposal ──────────────────────────────────────────
    if intent == "service_request":
        item = _match_catalog_item(message)
        if not item:
            item = {
                "id": "cat-103",
                "name": "Docker Desktop Commercial License",
                "category": "Software & Licenses",
                "requires_approval": True,
            }

        clean_msg = message.strip()
        justification = clean_msg if len(clean_msg) > 15 else f"Standard business need for {item['name']} by {user_name}."

        proposal = {
            "type": "create_service_request",
            "catalog_item_id": item["id"],
            "item_name": item["name"],
            "category": item["category"],
            "justification": justification,
            "requester": user_name,
            "details": {
                "item_name": item["name"],
                "category": item["category"],
                "business_justification": justification,
                "requester": user_name,
            },
        }

        approval_notice = "Requires manager approval before license allocation." if item.get("requires_approval") else "Pre-approved automated fulfillment item."

        proposal_text = (
            f"I have prepared a **Proposed Service Request** for **{item['name']}**:\n\n"
            f"• **Item**: {item['name']}\n"
            f"• **Category**: {item['category']}\n"
            f"• **Requester**: {user_name}\n"
            f"• **Justification**: {justification}\n"
            f"• **Approval Policy**: {approval_notice}\n\n"
            "Would you like me to submit this request? Reply **\"Yes\"** or **\"Confirm\"** to proceed."
        )

        return ChatResponse(
            message=proposal_text,
            matched_articles=[],
            generation_mode="request_intake_proposal",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="service_request",
            action_proposed=proposal,
        )

    # ── 11. Confirm Service Request Action ────────────────────────────────────
    if intent == "confirm_service_request":
        # Duplicate confirmation guardrail
        already_done = _get_recently_completed_action(history)
        if already_done and already_done[0] == "service request":
            return ChatResponse(
                message=f"✅ Service request **{already_done[1]}** has already been submitted! No duplicate request was created.",
                matched_articles=[],
                generation_mode="already_confirmed",
                llm_used=False,
                vector_database="none",
                has_answer=True,
                intent="confirm_without_proposal",
            )

        prior_user_msg = next((h.content for h in reversed(history) if h.role == "user" and len(h.content) > 5), "Standard IT request")
        item = _match_catalog_item(prior_user_msg) or {
            "id": "cat-103",
            "name": "Docker Desktop Commercial License",
            "category": "Software & Licenses",
        }

        try:
            req_payload = ServiceRequestCreate(
                catalog_item_id=item["id"],
                item_name=item["name"],
                category=RequestCategory(item.get("category", "Software & Licenses")),
                justification=f"Approved request initiated via HelpWise AI Assistant: {prior_user_msg}",
                business_justification=f"Approved request initiated via HelpWise AI Assistant: {prior_user_msg}",
                requester=user_name,
                department="Engineering",
            )
            created_req = await database.create_service_request(req_payload, actor=user_name)
            success_text = (
                f"🎉 **Service Request Successfully Submitted!**\n\n"
                f"• **Request Number**: `{created_req.request_number}`\n"
                f"• **Item**: {created_req.item_name}\n"
                f"• **Status**: `{created_req.status.value}`\n"
                f"• **Requester**: {created_req.requester}\n\n"
                "You can track this item under the **Service Requests** section. An IT administrator will review it shortly."
            )
            return ChatResponse(
                message=success_text,
                matched_articles=[],
                generation_mode="request_created",
                llm_used=False,
                vector_database="none",
                has_answer=True,
                intent="service_request",
                action_result={
                    "success": True,
                    "type": "service_request_created",
                    "record_type": "service_request",
                    "record_id": created_req.request_number,
                },
            )
        except Exception as exc:
            return ChatResponse(
                message=f"Could not submit service request: {str(exc)}",
                matched_articles=[],
                generation_mode="error",
                llm_used=False,
                vector_database="none",
                has_answer=False,
                intent="service_request",
            )

    # ── 12. Self-Heal Diagnostics Trigger ─────────────────────────────────────
    if intent == "diagnostic":
        report = diagnostics.run_network_diagnostics()
        steps_summary = "\n".join([f"• `{s.name}`: {'✅ Passed' if s.status == 'passed' else '⚠️ ' + s.status.upper()} ({s.details})" for s in report.steps])
        diag_text = (
            f"🔍 **Self-Heal Network Diagnostic Results** (Status: `{report.overall_status.upper()}`):\n\n"
            f"{steps_summary}\n\n"
            f"💡 **Recommendation**: {report.steps[-1].remediation or 'All systems operational.'}"
        )
        return ChatResponse(
            message=diag_text,
            matched_articles=[],
            generation_mode="diagnostic_executed",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="diagnostic",
        )

    # ── 13. Default: Knowledge Base RAG ───────────────────────────────────────
    rag_response = rag.answer_with_history(
        message=message,
        history=history,
        articles=articles,
    )
    rag_response.intent = "knowledge_search"

    # Repetition detector: if the RAG answer repeats the immediate previous assistant message,
    # or repeats an article that was already provided in this conversation, redirect to progressive next steps
    last_asst_content = next((h.content for h in reversed(history) if h.role == "assistant"), "")
    prior_articles_seen = [
        h.content for h in history if h.role == "assistant" and "Knowledge Base for" in h.content
    ]
    is_repeated = bool(last_asst_content) and (
        rag_response.message.strip() == last_asst_content.strip()
        or (len(rag_response.message) > 40 and rag_response.message[:60] in last_asst_content)
        or (rag_response.matched_articles and any(rag_response.matched_articles[0].title in p for p in prior_articles_seen))
    )

    if is_repeated:
        topic = _detect_context_topic(history, message)
        hit = _get_article_for_topic(topic, articles)
        matched = [hit] if hit else []
        prog_text = (
            "Since you're still experiencing this issue after the previous steps, let's move to advanced diagnostics:\n\n"
            "1. **Isolate Network**: Test on your mobile phone's hotspot to rule out home Wi-Fi/router blocks.\n"
            "2. **Self-Heal Diagnostic**: We can run an automated network and DNS latency test.\n"
            "3. **IT Incident Ticket**: I can log an official ticket so a network engineer can inspect your logs.\n\n"
            "Would you like to run network diagnostics or open a ticket?"
        )
        return ChatResponse(
            message=prog_text,
            matched_articles=matched,
            generation_mode="troubleshooting_escalation",
            llm_used=False,
            vector_database="none",
            has_answer=True,
            intent="troubleshooting_failed",
        )

    # Format extractive fallback responses in natural conversational tone
    if rag_response.has_answer and rag_response.generation_mode == "extractive_fallback" and rag_response.matched_articles:
        top_art = rag_response.matched_articles[0]
        friendly_answer = (
            f"Here is the recommended troubleshooting from our Knowledge Base for **{top_art.title}**:\n\n"
            f"**First step to try:**\n"
            f"• {top_art.content.strip()}\n\n"
            "**Additional tips:**\n"
            "• Ensure no personal VPN, proxy, or container networking tools are conflicting.\n"
            "• If you receive certificate or authentication errors, verify your device clock is synchronized.\n\n"
            "Let me know if this fixes it, or if you'd like me to run network diagnostics or log a ticket for IT Support!"
        )
        rag_response.message = friendly_answer

    return rag_response
