"""
migrate_tasks_sections.py — rename TASKS.md headings to new scheme.

Run from project root:
    python3 app/scripts/migrate_tasks_sections.py

Idempotent — safe to run multiple times.
"""

import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASKS_PATH = os.path.join(PROJECT_ROOT, "TASKS.md")

RENAMES = {
    "## Active":           "## Fundraising - Me",
    "## IR / FUNDRAISING": "## Fundraising - Me",
    "## WAITING ON":       "## Waiting On",
    "## OPERATIONS":       "## Work",
    "## PERSONAL":         "## Personal",
}


def migrate():
    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    changed = False
    new_lines = []
    for line in lines:
        stripped = line.rstrip()
        if stripped in RENAMES:
            new_heading = RENAMES[stripped] + "\n"
            if new_heading != line:
                print(f"Rename: {stripped!r} → {RENAMES[stripped]!r}")
                changed = True
            new_lines.append(new_heading)
        else:
            new_lines.append(line)

    # Ensure ## Work section exists after ## Fundraising - Me
    has_work = any(ln.rstrip() == "## Work" for ln in new_lines)
    if not has_work:
        insert_after = None
        for i, ln in enumerate(new_lines):
            if ln.rstrip() == "## Fundraising - Me":
                insert_after = i
                break
        if insert_after is not None:
            # Find where the next ## heading is
            next_heading = None
            for i in range(insert_after + 1, len(new_lines)):
                if re.match(r"^## ", new_lines[i]):
                    next_heading = i
                    break
            if next_heading is not None:
                new_lines.insert(next_heading, "\n")
                new_lines.insert(next_heading, "## Work\n")
            else:
                new_lines.append("\n## Work\n")
            print("Inserted empty ## Work section")
            changed = True

    if changed:
        with open(TASKS_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print("Done — TASKS.md updated.")
    else:
        print("No changes needed — TASKS.md already uses new headings.")


if __name__ == "__main__":
    migrate()
