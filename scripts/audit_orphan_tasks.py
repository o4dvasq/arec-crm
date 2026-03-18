#!/usr/bin/env python3
"""
audit_orphan_tasks.py — One-time read-only audit of TASKS.md.

Scans all open tasks (excluding Personal and Done sections) and flags
any that are missing an [org:] tag or an [owner:] tag. Writes a report
to docs/orphan_tasks_report.md. Does not modify TASKS.md.

Usage:
    python3 scripts/audit_orphan_tasks.py
"""

import os
import re
from datetime import date

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_MD_PATH = os.path.join(PROJECT_ROOT, 'TASKS.md')
REPORT_PATH = os.path.join(PROJECT_ROOT, 'docs', 'orphan_tasks_report.md')

SKIP_SECTIONS = {'personal', 'done'}


def audit():
    if not os.path.exists(TASKS_MD_PATH):
        print(f"ERROR: {TASKS_MD_PATH} not found")
        return

    orphans = []
    current_section = None

    with open(TASKS_MD_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for lineno, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped.startswith('## '):
            current_section = stripped[3:].strip()
            continue
        if current_section and current_section.lower() in SKIP_SECTIONS:
            continue
        if not stripped.startswith('- [ ]'):
            continue

        has_org = bool(re.search(r'\[org:\s*[^\]]+\]', stripped))
        has_owner = bool(re.search(r'\[owner:\s*[^\]]+\]', stripped))

        if not has_org or not has_owner:
            missing = []
            if not has_org:
                missing.append('[org:]')
            if not has_owner:
                missing.append('[owner:]')
            orphans.append({
                'lineno': lineno,
                'section': current_section or '(no section)',
                'text': stripped,
                'missing': ', '.join(missing),
            })

    # Write report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    today = date.today().isoformat()
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(f'# Orphan Tasks Report\n\n')
        f.write(f'Generated: {today}  \n')
        f.write(f'Source: `TASKS.md`  \n')
        f.write(f'Skipped sections: Personal, Done\n\n')
        f.write(f'---\n\n')

        if not orphans:
            f.write('**No orphan tasks found.** All open tasks have `[org:]` and `[owner:]` tags.\n')
        else:
            f.write(f'**{len(orphans)} task(s) flagged** — missing `[org:]` and/or `[owner:]` tags.\n\n')
            f.write('| Line | Section | Missing | Task Text |\n')
            f.write('|------|---------|---------|----------|\n')
            for o in orphans:
                text_escaped = o['text'].replace('|', '\\|')
                f.write(f"| {o['lineno']} | {o['section']} | {o['missing']} | `{text_escaped}` |\n")
            f.write('\n---\n\n')
            f.write('**Next step:** Manually add the missing tags to each flagged task before deploying the new Tasks UI.\n')

    # Print summary
    if orphans:
        print(f"{len(orphans)} tasks flagged — review {REPORT_PATH} before deploying")
    else:
        print(f"0 tasks flagged — all open tasks have [org:] and [owner:] tags")


if __name__ == '__main__':
    audit()
