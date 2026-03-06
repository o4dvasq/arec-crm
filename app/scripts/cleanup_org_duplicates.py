#!/usr/bin/env python3
"""
Cleanup script to remove duplicated org tags from tasks in TASKS.md

Finds patterns like:
  - "(OrgName) (OrgName)"
  - "(OrgName) — text — (OrgName) (OrgName)"
And reduces them to a single "(OrgName)" at the end.
"""

import re
import sys
from pathlib import Path

def cleanup_org_duplicates(line: str) -> tuple[str, bool]:
    """
    Remove duplicated org tags from a task line.
    Returns (cleaned_line, was_modified)
    """
    original = line

    # Pattern: Find all parenthetical org tags: (Something)
    # We'll collect all unique org names and keep only one at the end
    org_pattern = r'\(([^)]+)\)'

    # Find all org tags
    orgs = re.findall(org_pattern, line)

    if len(orgs) <= 1:
        # No duplicates possible
        return line, False

    # Check if there are actual duplicates
    unique_orgs = list(dict.fromkeys(orgs))  # Preserve first occurrence order

    if len(orgs) == len(unique_orgs):
        # No duplicates found
        return line, False

    # Remove all org tags from the line
    cleaned = re.sub(r'\s*\([^)]+\)', '', line)

    # Add back only the unique org tags (typically just one at the end)
    # Use the first unique org found
    if unique_orgs:
        # Find where to insert - before the line ending elements like —assigned:, —completed, etc.
        # Pattern: find the assignee/completion markers
        match = re.search(r'(\s+—\s*assigned:.*)', cleaned)
        if match:
            # Insert org tag before the assignee marker
            insert_pos = match.start()
            cleaned = cleaned[:insert_pos] + f' ({unique_orgs[0]})' + cleaned[insert_pos:]
        else:
            # Just append at the end
            cleaned = cleaned.rstrip() + f' ({unique_orgs[0]})'

    return cleaned, True

def main():
    tasks_file = Path(__file__).parent.parent.parent / 'TASKS.md'

    if not tasks_file.exists():
        print(f"Error: {tasks_file} not found")
        sys.exit(1)

    print(f"Reading {tasks_file}...")
    with open(tasks_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified_count = 0
    modified_lines = []

    for i, line in enumerate(lines, start=1):
        cleaned, was_modified = cleanup_org_duplicates(line)

        if was_modified:
            modified_count += 1
            print(f"\nLine {i}:")
            print(f"  Before: {line.rstrip()}")
            print(f"  After:  {cleaned.rstrip()}")
            modified_lines.append(i)

        lines[i-1] = cleaned

    if modified_count == 0:
        print("\nNo duplicated org tags found. Nothing to fix.")
        return

    print(f"\n{'='*60}")
    print(f"Found and fixed {modified_count} lines with duplicated org tags")
    print(f"Modified lines: {', '.join(map(str, modified_lines))}")

    # Write back
    backup_file = tasks_file.with_suffix('.md.bak.org_cleanup')
    print(f"\nCreating backup: {backup_file}")
    with open(backup_file, 'w', encoding='utf-8') as f:
        with open(tasks_file, 'r', encoding='utf-8') as orig:
            f.write(orig.read())

    print(f"Writing cleaned file: {tasks_file}")
    with open(tasks_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print("\n✓ Cleanup complete!")

if __name__ == '__main__':
    main()
