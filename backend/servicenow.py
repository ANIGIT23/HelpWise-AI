"""
ServiceNow Integration Adapter for HelpWise AI.

Supports official ServiceNow Table API integration (/api/now/table/incident).
If SERVICENOW_INSTANCE and credentials are not provided in .env, operates in
transparent Simulation Mode: constructs authentic ServiceNow REST payloads
and correlation IDs without breaking or fabricating fake live connections.
Never exposes credentials in logs, exceptions, or response objects.
"""

from __future__ import annotations

import os
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

logger = logging.getLogger("helpwise.servicenow")

# Load .env explicitly so vars are available regardless of working directory.
_ENV_FILE = Path(__file__).resolve().parent / ".env"

# Category mapping from HelpWise to standard ServiceNow categories
SN_CATEGORY_MAP = {
    "Hardware": "hardware",
    "Software": "software",
    "Network": "network",
    "Access": "inquiry",
    "Other": "inquiry",
}

# Priority mapping from HelpWise (1-4) to ServiceNow urgency/impact
SN_PRIORITY_MAP = {
    "Critical": ("1", "1"),  # 1-High urgency, 1-High impact -> Priority 1 Critical
    "High": ("2", "1"),      # Priority 2 High
    "Medium": ("2", "2"),    # Priority 3 Moderate
    "Low": ("3", "3"),       # Priority 4 Low
}

# ServiceNow numeric state codes -> human-readable labels
SN_STATE_MAP = {
    "1": "New",
    "2": "In Progress",
    "3": "On Hold",
    "6": "Resolved",
    "7": "Closed",
    "8": "Cancelled",
}


def _normalize_instance_url(raw: str) -> str:
    """
    Accepts various forms of ServiceNow instance identifier and returns
    the canonical base URL: 'https://dev461045.service-now.com'

    Handles:
      - 'dev461045'
      - 'dev461045.service-now.com'
      - 'https://dev461045.service-now.com'
      - 'https://dev461045.service-now.com/'
      - 'https://dev461045.service-now.com/api/now/...'
    """
    if not raw:
        return ""
    raw = raw.strip().rstrip("/")

    # Already a full HTTPS URL
    if raw.startswith("https://"):
        # Strip any path after the hostname
        parts = raw.split("/")
        return "/".join(parts[:3])  # https: + '' + hostname

    # Has http:// (upgrade to https)
    if raw.startswith("http://"):
        raw = raw[len("http://"):]

    # Remove .service-now.com if present (we'll add it back)
    subdomain = raw.replace(".service-now.com", "").strip()
    if not subdomain:
        return ""

    return f"https://{subdomain}.service-now.com"


def _get_config() -> Dict[str, Any]:
    """
    Re-reads ServiceNow configuration from environment/.env.
    Called on every request so config changes take effect immediately.
    Never returns passwords — only the caller's internal code uses them.
    """
    load_dotenv(dotenv_path=_ENV_FILE, override=True)

    instance_raw = os.getenv("SERVICENOW_INSTANCE", "").strip()
    user = os.getenv("SERVICENOW_USER", "").strip()
    password = os.getenv("SERVICENOW_PASSWORD", "").strip()

    instance_url = _normalize_instance_url(instance_raw)
    configured = bool(instance_url and user and password)

    return {
        "instance_url": instance_url,
        "user": user,
        "password": password,
        "configured": configured,
    }


# ---------------------------------------------------------------------------
# Status & Live Verification
# ---------------------------------------------------------------------------

def get_servicenow_status(check_live: bool = False) -> Dict[str, Any]:
    """
    Returns transparency status for ServiceNow integration.
    Never exposes passwords or tokens.

    If check_live=True and credentials are configured, performs an actual
    HTTP request to verify the instance is reachable and credentials work.
    """
    config = _get_config()

    if not config["configured"]:
        return {
            "configured": False,
            "mode": "simulation",
            "instance_url": None,
            "connection_verified": False,
            "message": "ServiceNow not configured. Operating in Simulation Mode.",
            "instructions": (
                "Configure SERVICENOW_INSTANCE, SERVICENOW_USER, and "
                "SERVICENOW_PASSWORD in backend/.env to activate live integration."
            ),
        }

    result: Dict[str, Any] = {
        "configured": True,
        "mode": "live",
        "instance_url": config["instance_url"],
        "connection_verified": False,
        "message": f"ServiceNow configured: {config['instance_url']}. Click 'Check Status' to verify connectivity.",
    }

    if check_live:
        import httpx
        try:
            url = f"{config['instance_url']}/api/now/table/incident"
            with httpx.Client(timeout=10.0) as client:
                res = client.get(
                    url,
                    params={"sysparm_limit": "1", "sysparm_fields": "number"},
                    auth=(config["user"], config["password"]),
                    headers={"Accept": "application/json"},
                )
            if res.status_code == 200:
                result["connection_verified"] = True
                result["message"] = f"Live connection verified to {config['instance_url']}."
            elif res.status_code == 401:
                result["message"] = "Authentication failed (HTTP 401). Check SERVICENOW_USER and SERVICENOW_PASSWORD."
            elif res.status_code == 403:
                result["message"] = "Access denied (HTTP 403). The account may lack the 'itil' role."
            else:
                result["message"] = f"ServiceNow returned HTTP {res.status_code}."
        except httpx.TimeoutException:
            result["message"] = (
                f"Connection timed out reaching {config['instance_url']}. "
                "Instance may be hibernating — open it in a browser first."
            )
        except httpx.ConnectError:
            result["message"] = f"Cannot connect to {config['instance_url']}. Check the URL and your network."
        except Exception as exc:
            result["message"] = f"Connection check failed: {type(exc).__name__}"

    return result


async def verify_servicenow_connection() -> Dict[str, Any]:
    """
    Async live connectivity test used by diagnostics and the verify endpoint.
    Returns reachable, authenticated, and descriptive message.
    """
    config = _get_config()

    if not config["configured"]:
        return {
            "reachable": False,
            "authenticated": False,
            "mode": "simulation",
            "message": "ServiceNow not configured. Simulation mode active.",
        }

    import httpx
    try:
        url = f"{config['instance_url']}/api/now/table/incident"
        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                url,
                params={"sysparm_limit": "1", "sysparm_fields": "number"},
                auth=(config["user"], config["password"]),
                headers={"Accept": "application/json"},
            )
        latency_ms = round((time.perf_counter() - start) * 1000, 1)

        if res.status_code == 200:
            return {
                "reachable": True,
                "authenticated": True,
                "mode": "live",
                "latency_ms": latency_ms,
                "instance_url": config["instance_url"],
                "message": f"Authenticated to {config['instance_url']} ({latency_ms} ms).",
            }
        elif res.status_code == 401:
            return {
                "reachable": True,
                "authenticated": False,
                "mode": "live",
                "latency_ms": latency_ms,
                "instance_url": config["instance_url"],
                "message": "Instance reachable but authentication failed (HTTP 401). Check credentials.",
            }
        elif res.status_code == 403:
            return {
                "reachable": True,
                "authenticated": False,
                "mode": "live",
                "latency_ms": latency_ms,
                "instance_url": config["instance_url"],
                "message": "Instance reachable but access denied (HTTP 403). Account may need 'itil' role.",
            }
        else:
            return {
                "reachable": True,
                "authenticated": False,
                "mode": "live",
                "instance_url": config["instance_url"],
                "message": f"Instance returned HTTP {res.status_code}.",
            }
    except httpx.TimeoutException:
        return {
            "reachable": False,
            "authenticated": False,
            "mode": "live",
            "instance_url": config["instance_url"],
            "message": (
                f"Connection timed out. Instance may be hibernating — "
                f"open {config['instance_url']} in your browser first."
            ),
        }
    except httpx.ConnectError:
        return {
            "reachable": False,
            "authenticated": False,
            "mode": "live",
            "instance_url": config["instance_url"],
            "message": f"Cannot reach {config['instance_url']}. Check URL and network.",
        }
    except Exception as exc:
        return {
            "reachable": False,
            "authenticated": False,
            "mode": "live",
            "instance_url": config["instance_url"],
            "message": f"Verification failed: {type(exc).__name__}",
        }


# ---------------------------------------------------------------------------
# Create Incident
# ---------------------------------------------------------------------------

async def create_servicenow_incident(
    title: str,
    description: str,
    category: str = "Software",
    priority: str = "Medium",
    caller_id: str = "Alex Morgan",
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates an incident in ServiceNow via the Table API.
    If live credentials are configured, calls the real REST endpoint.
    Otherwise produces a Table API payload in Simulation Mode.
    """
    config = _get_config()
    sn_cat = SN_CATEGORY_MAP.get(category, "inquiry")
    urgency, impact = SN_PRIORITY_MAP.get(priority, ("2", "2"))
    corr_id = correlation_id or f"HELPWISE-{int(time.time())}"

    payload = {
        "short_description": title.strip(),
        "description": description.strip(),
        "category": sn_cat,
        "urgency": urgency,
        "impact": impact,
        "caller_id": caller_id,
        "correlation_id": corr_id,
        "contact_type": "self-service",
    }

    # Live Mode
    if config["configured"]:
        try:
            import httpx
            url = f"{config['instance_url']}/api/now/table/incident"
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    url,
                    json=payload,
                    auth=(config["user"], config["password"]),
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
            if res.status_code in (200, 201):
                data = res.json().get("result", {})
                return {
                    "mode": "live",
                    "synced": True,
                    "sys_id": data.get("sys_id"),
                    "number": data.get("number"),
                    "state": SN_STATE_MAP.get(str(data.get("state", "")), "New"),
                    "correlation_id": corr_id,
                    "instance_url": config["instance_url"],
                }
            elif res.status_code == 401:
                return {
                    "mode": "live",
                    "synced": False,
                    "error": "authentication_failed",
                    "message": "ServiceNow rejected credentials (HTTP 401). Check SERVICENOW_USER and SERVICENOW_PASSWORD.",
                }
            elif res.status_code == 403:
                return {
                    "mode": "live",
                    "synced": False,
                    "error": "access_denied",
                    "message": "ServiceNow denied access (HTTP 403). The account may need the 'itil' role to create incidents.",
                }
            else:
                logger.warning(f"ServiceNow API returned status {res.status_code}")
                return {
                    "mode": "live",
                    "synced": False,
                    "error": f"http_{res.status_code}",
                    "message": f"ServiceNow returned HTTP {res.status_code}.",
                }
        except httpx.TimeoutException:
            return {
                "mode": "live",
                "synced": False,
                "error": "timeout",
                "message": f"Connection timed out. Instance at {config['instance_url']} may be hibernating.",
            }
        except httpx.ConnectError:
            return {
                "mode": "live",
                "synced": False,
                "error": "unreachable",
                "message": f"Cannot reach {config['instance_url']}. Check network and instance URL.",
            }
        except Exception as exc:
            logger.warning(f"ServiceNow live sync error: {type(exc).__name__}")
            return {
                "mode": "live",
                "synced": False,
                "error": "connection_error",
                "message": f"Connection error: {type(exc).__name__}",
            }

    # Simulation Mode
    seed = f"{corr_id}-{title}-{time.time()}"
    synthetic_sys_id = hashlib.md5(seed.encode()).hexdigest()
    synthetic_number = f"INC{int(time.time()) % 1000000:07d}"

    return {
        "mode": "simulation",
        "synced": True,
        "sys_id": synthetic_sys_id,
        "number": synthetic_number,
        "correlation_id": corr_id,
        "instance_url": None,
        "payload": payload,
        "message": "Simulated ServiceNow incident (no live instance configured).",
    }


# ---------------------------------------------------------------------------
# Fetch Incident
# ---------------------------------------------------------------------------

async def fetch_servicenow_incident(number: str) -> Dict[str, Any]:
    """
    Fetches an incident from ServiceNow by its number (e.g. 'INC0010001').
    Returns key fields without exposing credentials.
    """
    config = _get_config()

    if not config["configured"]:
        return {
            "mode": "simulation",
            "found": False,
            "message": "ServiceNow not configured. Cannot fetch real incidents in Simulation Mode.",
        }

    if not number or not number.strip():
        return {
            "mode": "live",
            "found": False,
            "message": "Incident number is required.",
        }

    clean_number = number.strip().upper()

    import httpx
    try:
        url = f"{config['instance_url']}/api/now/table/incident"
        params = {
            "sysparm_query": f"number={clean_number}",
            "sysparm_fields": (
                "number,short_description,description,state,priority,"
                "urgency,impact,category,assigned_to,caller_id,"
                "sys_created_on,sys_updated_on,close_code,close_notes"
            ),
            "sysparm_display_value": "true",
            "sysparm_limit": "1",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                url,
                params=params,
                auth=(config["user"], config["password"]),
                headers={"Accept": "application/json"},
            )

        if res.status_code == 200:
            results = res.json().get("result", [])
            if not results:
                return {
                    "mode": "live",
                    "found": False,
                    "message": f"No incident found with number '{clean_number}' on {config['instance_url']}.",
                }
            inc = results[0]
            return {
                "mode": "live",
                "found": True,
                "number": inc.get("number"),
                "short_description": inc.get("short_description"),
                "state": inc.get("state", ""),
                "priority": inc.get("priority", ""),
                "urgency": inc.get("urgency", ""),
                "impact": inc.get("impact", ""),
                "category": inc.get("category", ""),
                "assigned_to": inc.get("assigned_to", ""),
                "caller_id": inc.get("caller_id", ""),
                "created_on": inc.get("sys_created_on", ""),
                "updated_on": inc.get("sys_updated_on", ""),
                "close_code": inc.get("close_code", ""),
                "close_notes": inc.get("close_notes", ""),
                "instance_url": config["instance_url"],
            }
        elif res.status_code == 401:
            return {
                "mode": "live",
                "found": False,
                "message": "Authentication failed (HTTP 401). Check ServiceNow credentials.",
            }
        elif res.status_code == 403:
            return {
                "mode": "live",
                "found": False,
                "message": "Access denied (HTTP 403). Account may need 'itil' role.",
            }
        else:
            return {
                "mode": "live",
                "found": False,
                "message": f"ServiceNow returned HTTP {res.status_code}.",
            }
    except httpx.TimeoutException:
        return {
            "mode": "live",
            "found": False,
            "message": f"Connection timed out reaching {config['instance_url']}.",
        }
    except httpx.ConnectError:
        return {
            "mode": "live",
            "found": False,
            "message": f"Cannot connect to {config['instance_url']}.",
        }
    except Exception as exc:
        return {
            "mode": "live",
            "found": False,
            "message": f"Error fetching incident: {type(exc).__name__}",
        }
