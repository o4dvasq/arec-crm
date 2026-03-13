"""
Parse crm/TASKS.md and insert all prospect-specific tasks into the prospect_tasks
PostgreSQL table. Also create any missing organizations and prospects for tasks
that reference orgs not yet in the database.

Usage:
  python3 scripts/migrate_tasks_to_postgres.py              # Normal mode (with confirmation)
  python3 scripts/migrate_tasks_to_postgres.py --dry-run    # Dry-run mode (parse only, no DB)
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Add app/ to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app')
sys.path.insert(0, APP_DIR)

# Must load dotenv before importing db
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', '.env')
    load_dotenv(env_path)
except ImportError:
    pass

from db import init_db, get_session, session_scope
from models import Organization, Prospect, ProspectTask, Offering, User


# ============================================================================
# Parsing Logic
# ============================================================================

def parse_tasks_md(filepath: str) -> Tuple[List[Dict], List[str]]:
    """
    Parse crm/TASKS.md and extract all prospect-specific tasks.

    Returns:
        (tasks_list, warnings)

        tasks_list: List of dicts with keys:
            - org_name: str (bolded text before colon)
            - text: str (task description)
            - owner: str (first name only, e.g. "Oscar", "Max")
            - priority: str ("High" or "Med")
            - status: str ("open" or "done")

        warnings: List of skipped lines with reasons
    """
    tasks = []
    warnings = []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_owner = None
    current_section = None

    for i, line in enumerate(lines, 1):
        line = line.rstrip('\n')

        # Parse owner header: "## Person Name — ..." or "## Person Name – ..."
        # Extract first name only. Handles em-dash, en-dash, and regular dash.
        owner_match = re.match(r'^## ([A-Za-z]+)\s+\w+', line)
        if owner_match:
            current_owner = owner_match.group(1)
            current_section = None
            continue

        # Parse subsection header: "### ..."
        subsection_match = re.match(r'^### (.+)$', line)
        if subsection_match:
            current_section = subsection_match.group(1)
            continue

        # Parse task line: "- [ ] **Org Name:** Task text" or "- [x] **Org Name:** Task text"
        # The colon is part of the ** pair: **Org Name:**
        task_match = re.match(r'^- \[([ x])\] \*\*(.+):\*\*\s*(.+)$', line)
        if task_match:
            is_done = task_match.group(1).lower() == 'x'
            org_name = task_match.group(2).strip()
            task_text = task_match.group(3).strip()

            # Determine priority based on section and owner
            priority = 'Med'  # default

            # Hot / Immediate tasks are High priority
            if current_section and ('Hot' in current_section or 'Immediate' in current_section):
                priority = 'High'
            # Oscar's direct items (no subsection) are High priority
            elif current_owner == 'Oscar' and current_section is None:
                priority = 'High'
            # Ongoing European Pipeline is Med
            elif current_section and 'Ongoing' in current_section:
                priority = 'Med'

            status = 'done' if is_done else 'open'

            # Skip generic directives (don't have org_name pattern)
            # E.g., "Send prioritized investor list", "Include Oscar or Tony on all first calls"
            # These are identified by lacking a clear org reference or being all-caps directives
            if not org_name or org_name.startswith('Send ') or org_name.startswith('Include '):
                warnings.append(
                    f"Line {i}: Skipped (not a prospect task): {org_name}"
                )
                continue

            task = {
                'org_name': org_name,
                'text': task_text,
                'owner': current_owner or '',
                'priority': priority,
                'status': status,
            }
            tasks.append(task)
            continue

        # Skip non-matching lines (headers, empty lines, etc.)

    return tasks, warnings


def build_preview_table(tasks: List[Dict]) -> str:
    """Build a formatted table for preview."""
    if not tasks:
        return "(No tasks to insert)"

    # Truncate text to 60 chars for preview
    rows = []
    for task in tasks:
        text_preview = task['text'][:60] + ('...' if len(task['text']) > 60 else '')
        rows.append({
            'Org': task['org_name'][:25] + ('...' if len(task['org_name']) > 25 else ''),
            'Task': text_preview,
            'Owner': task['owner'],
            'Priority': task['priority'],
            'Status': task['status'],
        })

    # Build table
    headers = ['Org', 'Task', 'Owner', 'Priority', 'Status']
    col_widths = {h: len(h) for h in headers}

    for row in rows:
        for header in headers:
            col_widths[header] = max(col_widths[header], len(str(row.get(header, ''))))

    # Format header
    header_line = '  '.join(f"{h:<{col_widths[h]}}" for h in headers)
    sep_line = '  '.join('-' * col_widths[h] for h in headers)

    lines = [header_line, sep_line]
    for row in rows:
        row_line = '  '.join(f"{row.get(h, ''):<{col_widths[h]}}" for h in headers)
        lines.append(row_line)

    return '\n'.join(lines)


# ============================================================================
# Database Logic
# ============================================================================

def find_or_create_org(session, org_name: str) -> Optional[int]:
    """
    Check if an Organization exists (case-insensitive).
    If not, create one with type='Investor'.

    Returns: org_id or None if creation fails
    """
    # Case-insensitive search
    existing = session.query(Organization).filter(
        Organization.name.ilike(org_name)
    ).first()

    if existing:
        return existing.id

    # Create new org
    new_org = Organization(
        name=org_name,
        type='Investor',
        domain='',
        notes='',
        created_at=datetime.utcnow(),
    )
    session.add(new_org)
    session.flush()  # Get the ID without committing
    return new_org.id


def find_or_create_prospect(session, org_id: int, assigned_to_user_id: Optional[int]) -> Optional[int]:
    """
    Check if a Prospect exists for org_id + default offering.
    If not, create one with stage='1. Prospect', target=0.

    Returns: prospect_id or None if creation fails
    """
    # Get offerings to determine which one to use
    offerings = session.query(Offering).all()
    if not offerings:
        return None  # No offerings exist, can't create prospect

    # Prioritize "Debt Fund II" or use the first offering
    offering = None
    for o in offerings:
        if 'Debt Fund II' in o.name:
            offering = o
            break
    if not offering:
        offering = offerings[0]

    # Check if prospect already exists
    existing = session.query(Prospect).filter(
        Prospect.organization_id == org_id,
        Prospect.offering_id == offering.id
    ).first()

    if existing:
        return existing.id

    # Create new prospect
    new_prospect = Prospect(
        organization_id=org_id,
        offering_id=offering.id,
        stage='1. Prospect',
        target=0,
        assigned_to=assigned_to_user_id,
        created_at=datetime.utcnow(),
    )
    session.add(new_prospect)
    session.flush()
    return new_prospect.id


def find_user_by_firstname(session, firstname: str) -> Optional[int]:
    """Find a user by first name (assumes display_name is "FirstName LastName")."""
    if not firstname:
        return None

    users = session.query(User).all()
    for user in users:
        parts = user.display_name.split()
        if parts and parts[0].lower() == firstname.lower():
            return user.id
    return None


def check_duplicate_task(session, org_name: str, task_text: str) -> bool:
    """Check if a task with same org_name and text already exists."""
    existing = session.query(ProspectTask).filter(
        ProspectTask.org_name.ilike(org_name),
        ProspectTask.text == task_text
    ).first()
    return existing is not None


def insert_tasks(tasks: List[Dict], dry_run: bool = False) -> Tuple[int, int, int]:
    """
    Insert tasks into prospect_tasks table.
    Also create missing orgs and prospects.

    Returns: (tasks_inserted, orgs_created, prospects_created)
    """
    if dry_run:
        print("DRY RUN MODE: No database changes")
        return 0, 0, 0

    tasks_inserted = 0
    orgs_created = 0
    prospects_created = 0

    with session_scope() as session:
        for task in tasks:
            org_name = task['org_name']
            task_text = task['text']
            owner = task['owner']
            priority = task['priority']
            status = task['status']

            # Check for duplicate
            if check_duplicate_task(session, org_name, task_text):
                print(f"  Skipping duplicate: {org_name} / {task_text[:40]}...")
                continue

            # Find or create org
            org_exists = session.query(Organization).filter(
                Organization.name.ilike(org_name)
            ).first() is not None
            org_id = find_or_create_org(session, org_name)
            if org_id is None:
                print(f"  ERROR: Could not create org {org_name}")
                continue
            if not org_exists:
                orgs_created += 1

            # Find or create prospect
            user_id = find_user_by_firstname(session, owner)
            prospect_exists = session.query(Prospect).filter(
                Prospect.organization_id == org_id
            ).first() is not None
            prospect_id = find_or_create_prospect(session, org_id, user_id)
            if prospect_id and not prospect_exists:
                prospects_created += 1

            # Insert task
            new_task = ProspectTask(
                org_name=org_name,
                text=task_text,
                owner=owner,
                priority=priority,
                status=status,
                created_at=datetime.utcnow(),
            )
            session.add(new_task)
            tasks_inserted += 1

    return tasks_inserted, orgs_created, prospects_created


# ============================================================================
# Main
# ============================================================================

def main():
    # Check for help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    dry_run = '--dry-run' in sys.argv

    # Resolve paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    tasks_md_path = os.path.join(project_root, 'crm', 'TASKS.md')

    if not os.path.exists(tasks_md_path):
        print(f"ERROR: {tasks_md_path} not found")
        sys.exit(1)

    print("=" * 80)
    print("AREC-CRM Task Migration Script")
    print("=" * 80)
    print()

    # Parse TASKS.md
    print(f"Parsing {tasks_md_path}...")
    tasks, warnings = parse_tasks_md(tasks_md_path)

    print(f"Found {len(tasks)} prospect-specific tasks")
    if warnings:
        print(f"Skipped {len(warnings)} non-prospect items")
    print()

    # Show preview
    print("Preview of tasks to be inserted:")
    print("-" * 80)
    print(build_preview_table(tasks))
    print("-" * 80)
    print()

    # Count unique orgs (approximate)
    unique_orgs = len(set(t['org_name'] for t in tasks))
    print(f"Total unique organizations: {unique_orgs}")
    print()

    if dry_run:
        print("DRY RUN: Parsing complete. No database changes made.")
        return

    # Ask for confirmation
    print("This will insert tasks and create missing orgs/prospects.")
    response = input("Proceed? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return

    # Initialize database
    try:
        init_db()
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Insert tasks
    print()
    print("Inserting tasks...")
    tasks_inserted, orgs_created, prospects_created = insert_tasks(tasks, dry_run=False)

    print()
    print("=" * 80)
    print("Migration Summary")
    print("=" * 80)
    print(f"Tasks inserted:      {tasks_inserted}")
    print(f"Orgs created:        {orgs_created}")
    print(f"Prospects created:   {prospects_created}")
    print("=" * 80)


if __name__ == '__main__':
    main()
