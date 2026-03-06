#!/usr/bin/env python3
"""
Migration script: Add status field to all tasks in TASKS.md

This script adds the status field to all existing tasks that don't have one.
Default status: "open" for uncompleted tasks, "complete" for completed tasks.

Run: python app/scripts/migrate_tasks_status.py
"""

import os
import re
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASKS_PATH = os.path.join(PROJECT_ROOT, 'TASKS.md')


def migrate_status():
    """Add status markers to tasks that don't have them."""
    if not os.path.exists(TASKS_PATH):
        print(f"Error: {TASKS_PATH} not found")
        return

    with open(TASKS_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    updated = 0
    new_lines = []

    for line in lines:
        # Only process task lines
        if line.startswith('- [ ] ') or line.startswith('- [x] '):
            # Check if already has status marker
            if '[STATUS:' in line:
                new_lines.append(line)
                continue

            # Parse task
            done = line.startswith('- [x] ')
            checkbox = '- [x] ' if done else '- [ ] '
            rest = line[6:].rstrip()

            # Default status: open for uncompleted, complete for completed
            # Note: we don't add explicit markers for "open" to keep markdown clean
            # The parser defaults to "open" for tasks without markers
            if done:
                # Completed tasks get explicit complete marker
                # Insert after priority but before text
                pm = re.match(r'(\*\*\[\w+\]\*\*\s*)', rest)
                if pm:
                    priority_part = pm.group(1)
                    rest_part = rest[pm.end():]
                    new_line = f'{checkbox}{priority_part}[STATUS:complete] {rest_part}\n'
                else:
                    new_line = f'{checkbox}[STATUS:complete] {rest}\n'
                new_lines.append(new_line)
                updated += 1
            else:
                # Open tasks don't need explicit marker (parser defaults to "open")
                new_lines.append(line)

        else:
            new_lines.append(line)

    # Write back
    with open(TASKS_PATH, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f'Migration complete: {updated} tasks updated with status markers')


if __name__ == '__main__':
    migrate_status()
