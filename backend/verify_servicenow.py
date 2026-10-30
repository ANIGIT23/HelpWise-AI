"""
Quick verification script for ServiceNow Table API integration.
Tests instance connectivity and authentication safely without exposing secrets.
"""

import sys
import asyncio
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

import servicenow


async def main():
    print("=" * 60)
    print("  HelpWise AI — ServiceNow Integration Verifier")
    print("=" * 60)

    cfg = servicenow._get_config()
    print(f"Configured Instance: {cfg['instance_url'] or '(Not set)'}")
    print(f"User:                {cfg['user'] or '(Not set)'}")
    print(f"Password set:        {'Yes (Hidden)' if cfg['password'] else 'No (Empty)'}")
    print("-" * 60)

    if not cfg["configured"]:
        print("STATUS: Unconfigured (Simulation Mode active)")
        print("Please set SERVICENOW_INSTANCE, SERVICENOW_USER, and SERVICENOW_PASSWORD in backend/.env")
        return

    print("Sending live test request to /api/now/table/incident...")
    res = await servicenow.verify_servicenow_connection()

    if res.get("authenticated"):
        print(f"SUCCESS! Authenticated to ServiceNow ({res.get('latency_ms')} ms)")
        print(f"Message: {res.get('message')}")
    else:
        print(f"FAILED: {res.get('message')}")
        if not res.get("reachable"):
            print("Tip: If the instance is hibernating, go to developer.servicenow.com and click 'Wake Instance'.")
        else:
            print("Tip: The instance is reachable, but the username or password was rejected (HTTP 401).")
            print("Remember: The username is 'admin', NOT your email address.")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

