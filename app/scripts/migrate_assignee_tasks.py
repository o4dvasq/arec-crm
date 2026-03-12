"""
migrate_assignee_tasks.py — One-time CRM data migration.

Steps:
  1. Scan prospects.md for multi-assignee records and prompt to resolve to one owner.
  2. Scan for Next Action fields, offer to convert to TASKS.md tasks, then remove.
  3. Write updated prospects.md.

Run from project root:
    python app/scripts/migrate_assignee_tasks.py
"""

import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "app"))

PROSPECTS_PATH = os.path.join(PROJECT_ROOT, "crm", "prospects.md")
TASKS_PATH = os.path.join(PROJECT_ROOT, "TASKS.md")

from sources.crm_db import load_prospects, write_prospect, get_prospect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_assignees(assigned_to: str) -> list[str]:
    """Return list of names if multi-assign (semicolon-separated), else []."""
    if ';' in assigned_to:
        parts = [n.strip() for n in assigned_to.split(';') if n.strip()]
        return parts if len(parts) > 1 else []
    return []


def _prompt_single_assignee(org: str, offering: str, assignees: list[str]) -> str | None:
    """Prompt user to choose a single owner. Returns chosen name or None to skip."""
    print(f"\n  Prospect: {org}  ({offering})")
    print(f"  Current: {' ; '.join(assignees)}")
    for i, name in enumerate(assignees, 1):
        print(f"    {i}. {name}")
    print(f"    s. Skip (keep as-is)")
    while True:
        raw = input("  Choose owner [1-{}|s]: ".format(len(assignees))).strip()
        if raw.lower() == 's':
            return None
        if raw in assignees:
            return raw
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(assignees):
                return assignees[idx]
        except ValueError:
            pass
        print(f"  Enter a number 1-{len(assignees)} or 's'.")


def _prompt_convert_next_action(org: str, offering: str, next_action: str) -> dict | None:
    """Prompt to convert a Next Action to a TASKS.md task.
    Returns task dict on yes, None on no.
    """
    print(f"\n  Next Action for {org} ({offering}):")
    print(f"    '{next_action}'")
    while True:
        choice = input("  Convert to TASKS.md task? [y/n]: ").strip().lower()
        if choice == 'n':
            return None
        if choice == 'y':
            break
        print("  Enter y or n.")

    owner = input("  Owner (default: Oscar Vasquez): ").strip() or "Oscar Vasquez"
    section = input("  Section (default: IR / Fundraising): ").strip() or "IR / Fundraising"
    priority_raw = input("  Priority — Hi/Med/Lo (default: Med): ").strip() or "Med"
    priority = priority_raw if priority_raw in ("Hi", "Med", "Lo", "Low") else "Med"
    return {'text': next_action, 'owner': owner, 'section': section, 'priority': priority}


def _append_task(org: str, task: dict) -> None:
    """Write a prospect task line to TASKS.md."""
    line = f"- [ ] **[{task['priority']}]** {task['text']} — [org: {org}] [owner: {task['owner']}]\n"
    with open(TASKS_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    target = f"## {task['section']}"
    inserted = False
    for i, ln in enumerate(lines):
        if ln.strip() == target:
            lines.insert(i + 1, line)
            inserted = True
            break
    if not inserted:
        lines.append(f"\n## {task['section']}\n")
        lines.append(line)
    with open(TASKS_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"  → Added to TASKS.md under '{task['section']}'")


# ---------------------------------------------------------------------------
# Main migration
# ---------------------------------------------------------------------------

def migrate():
    print("=" * 60)
    print("CRM Data Migration: Single Assignee + Next Action Cleanup")
    print("=" * 60)

    prospects = load_prospects()
    print(f"\nLoaded {len(prospects)} prospect records.\n")

    # ------------------------------------------------------------------
    # Step 1 — Resolve multi-assignees
    # ------------------------------------------------------------------
    print("Step 1 — Scanning for multi-assignee prospects...\n")
    multi_prospects = [
        p for p in prospects
        if _split_assignees(p.get('Assigned To', ''))
    ]
    print(f"  Found {len(multi_prospects)} prospects with multiple assignees.")

    updated_count = 0
    skipped_count = 0
    for p in multi_prospects:
        org = p['org']
        offering = p['offering']
        assignees = _split_assignees(p.get('Assigned To', ''))
        chosen = _prompt_single_assignee(org, offering, assignees)
        if chosen is None:
            print(f"  Skipped.")
            skipped_count += 1
            continue
        # Read fresh copy, set new owner, write back
        fresh = get_prospect(org, offering)
        if fresh:
            fresh['Assigned To'] = chosen
            # Remove Next Action if present (write_prospect won't write it)
            fresh.pop('Next Action', None)
            write_prospect(org, offering, fresh)
            print(f"  ✓ {org}: set owner to '{chosen}'")
            updated_count += 1

    print(f"\nStep 1 done — {updated_count} updated, {skipped_count} skipped.")

    # ------------------------------------------------------------------
    # Step 2 — Convert Next Action fields
    # ------------------------------------------------------------------
    print("\nStep 2 — Scanning for Next Action fields...\n")
    # Reload after step 1 changes
    prospects = load_prospects()
    na_prospects = [
        p for p in prospects
        if p.get('Next Action', '').strip()
    ]
    print(f"  Found {len(na_prospects)} prospects with a Next Action value.")

    converted_count = 0
    dropped_count = 0
    for p in na_prospects:
        org = p['org']
        offering = p['offering']
        next_action = p['Next Action'].strip()
        task_info = _prompt_convert_next_action(org, offering, next_action)
        if task_info:
            _append_task(org, task_info)
            converted_count += 1
        else:
            print(f"  Dropped Next Action for {org}.")
            dropped_count += 1
        # Write back to strip Next Action field (write_prospect ignores it)
        fresh = get_prospect(org, offering)
        if fresh:
            fresh.pop('Next Action', None)
            write_prospect(org, offering, fresh)

    print(f"\nStep 2 done — {converted_count} converted to tasks, {dropped_count} dropped.")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"  Assignees resolved: {updated_count}")
    print(f"  Assignees skipped:  {skipped_count}")
    print(f"  Next Actions → tasks: {converted_count}")
    print(f"  Next Actions dropped: {dropped_count}")
    print("\nDone. Review prospects.md and TASKS.md to confirm changes.")


if __name__ == "__main__":
    migrate()
