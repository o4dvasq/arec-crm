#!/usr/bin/env python3
"""
refresh_interested_briefs.py

Fetches all prospects in Stage "5. Interested" and runs a full Relationship
Brief Refresh (narrative + At a Glance) for each one via the local dashboard API.

Usage:
    python scripts/refresh_interested_briefs.py [--base-url http://localhost:3001] [--dry-run]

Options:
    --base-url    Dashboard base URL (default: http://localhost:3001)
    --dry-run     List matching prospects without calling the API
    --delay       Seconds between API calls (default: 3, to avoid rate limits)
"""

import argparse
import sys
import time
import requests

TARGET_STAGE = "5. Interested"
DEFAULT_BASE_URL = "http://localhost:3001"
DEFAULT_DELAY = 3  # seconds between Claude API calls


def get_prospects(base_url: str) -> list[dict]:
    """Fetch all prospects from the dashboard API."""
    url = f"{base_url}/crm/api/prospects"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"❌  Cannot connect to dashboard at {base_url}")
        print("    Make sure the app is running: python app/main.py")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌  HTTP error fetching prospects: {e}")
        sys.exit(1)
    return resp.json()


def refresh_brief(base_url: str, org: str, offering: str) -> dict:
    """POST to synthesize-brief with generate_glance=True (Refresh mode)."""
    url = f"{base_url}/crm/api/synthesize-brief"
    payload = {
        "org": org,
        "offering": offering,
        "generate_glance": True,
    }
    resp = requests.post(url, json=payload, timeout=120)  # Claude calls can be slow
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Refresh briefs for Stage 5. Interested prospects")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--dry-run", action="store_true", help="List matches, no API calls")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help=f"Seconds between calls (default: {DEFAULT_DELAY})")
    args = parser.parse_args()

    print(f"🔍  Fetching prospects from {args.base_url} ...")
    all_prospects = get_prospects(args.base_url)

    interested = [p for p in all_prospects if p.get("Stage") == TARGET_STAGE]

    if not interested:
        print(f"ℹ️   No prospects found in Stage '{TARGET_STAGE}'.")
        return

    print(f"\n📋  Found {len(interested)} prospect(s) in Stage '{TARGET_STAGE}':\n")
    for i, p in enumerate(interested, 1):
        org      = p.get("org", "?")
        offering = p.get("offering", "?")
        glance   = p.get("at_a_glance", "")
        glance_display = f"  ⚡ {glance}" if glance else "  (no glance yet)"
        print(f"  {i:2d}. [{offering}]  {org}")
        print(f"      {glance_display}")

    if args.dry_run:
        print(f"\n⚠️   Dry-run mode — no briefs refreshed.")
        return

    print(f"\n🚀  Starting refresh ({args.delay}s delay between calls) ...\n")
    results = {"ok": [], "failed": []}

    for i, p in enumerate(interested, 1):
        org      = p.get("org", "?")
        offering = p.get("offering", "?")

        print(f"  [{i}/{len(interested)}] {org}  ({offering})")
        print(f"         ⏳ Calling Claude ...", end="", flush=True)

        try:
            result = refresh_brief(args.base_url, org, offering)
            glance = result.get("at_a_glance", "")
            print(f"\r         ✅ Done")
            if glance:
                print(f"         ⚡ {glance}")
            results["ok"].append(org)
        except requests.exceptions.HTTPError as e:
            print(f"\r         ❌ HTTP error: {e}")
            results["failed"].append((org, str(e)))
        except Exception as e:
            print(f"\r         ❌ Error: {e}")
            results["failed"].append((org, str(e)))

        if i < len(interested):
            time.sleep(args.delay)

    # ── Summary ────────────────────────────────────────────────────────
    print(f"\n{'─'*55}")
    print(f"✅  Refreshed:  {len(results['ok'])}/{len(interested)}")
    if results["failed"]:
        print(f"❌  Failed ({len(results['failed'])}):")
        for org, err in results["failed"]:
            print(f"    • {org}: {err}")
    print(f"{'─'*55}")


if __name__ == "__main__":
    main()
