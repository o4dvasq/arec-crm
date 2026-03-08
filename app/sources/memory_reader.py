"""
memory_reader.py — Reads Dropbox markdown files for briefing injection (CC-05)
"""

import os
import re

PRODUCTIVITY_ROOT = os.path.expanduser("~/Dropbox/Tech/ClaudeProductivity")


def load_tasks(section: str = None) -> dict:
    """
    Parse TASKS.md → {'fundraising': [...], 'personal': [...], 'waiting': [...], 'work': [...]}
    Each item is a string like '[Hi] Follow up with Jared Brimberry (UTIMCO)'

    Pass section= to filter to a single key (e.g. section='fundraising').
    """
    path = os.path.join(PRODUCTIVITY_ROOT, "TASKS.md")
    if not os.path.exists(path):
        return {"fundraising": [], "personal": [], "work": []}

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    tasks = {"fundraising": [], "personal": [], "work": []}
    section_map = {
        "fundraising - me":     "fundraising",
        "fundraising - others": "fundraising",
        "other work":           "work",
        "personal":             "personal",
        "work":                 "work",
    }
    current_section = None

    for line in content.splitlines():
        h2 = re.match(r"^## (.+)", line)
        if h2:
            heading_lower = h2.group(1).strip().lower()
            current_section = section_map.get(heading_lower)
            continue

        if current_section and line.startswith("- [ ]"):
            # Strip checkbox syntax: '- [ ] **[Hi]** text' → '[Hi] text'
            task_text = line[5:].strip()
            # Remove bold markdown from priority tag
            task_text = re.sub(r"\*\*(\[[^\]]+\])\*\*", r"\1", task_text)
            tasks[current_section].append(task_text)

    if section:
        key = section.lower().replace(" ", "_").replace("-", "_")
        return {k: v for k, v in tasks.items() if k == key}
    return tasks


def load_memory_summary() -> str:
    """
    Read CLAUDE.md from the project root. Returns up to 2000 chars.
    This provides Oscar's identity, team, and business context for the briefing.
    """
    path = os.path.join(PRODUCTIVITY_ROOT, "CLAUDE.md")
    if not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return content[:2000]


def load_inbox() -> list[str]:
    """
    Parse inbox.md → list of pending items (may be empty).
    Skips comment lines and blank lines.
    """
    path = os.path.join(PRODUCTIVITY_ROOT, "inbox.md")
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    items = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("<!--"):
            continue
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif line:
            items.append(line)

    return items


def update_task_status(section: str, task_text: str, new_status: str) -> bool:
    """
    Find task by section + text, rewrite its line to reflect new_status.
    new_status: "New" | "In Progress" | "Complete"
    Returns True on success, False if task not found.
    """
    path = os.path.join(PRODUCTIVITY_ROOT, "TASKS.md")
    if not os.path.exists(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_section = None
    task_found = False

    for i, line in enumerate(lines):
        # Check if we're entering a section
        h2 = re.match(r"^## (.+)", line)
        if h2:
            current_section = h2.group(1).strip()
            continue

        # Skip if not in the target section
        if current_section != section:
            continue

        # Check if this is a task line
        if not (line.startswith("- [ ] ") or line.startswith("- [x] ")):
            continue

        # Parse the task text (strip checkbox, priority, status tag, context)
        parsed_text = line[6:].strip()  # Remove checkbox

        # Remove priority tag
        parsed_text = re.sub(r"^\*\*\[[^\]]+\]\*\*\s*", "", parsed_text)

        # Remove status tag if present
        parsed_text = re.sub(r"^\*\*\[→\]\*\*\s*", "", parsed_text)

        # Extract just the task text (before — context)
        text_only = parsed_text.split(" — ")[0].strip()

        # Remove (OrgName) suffix for matching (same as dashboard parser does)
        text_for_match = re.sub(r'\s*\([^)]+\)\s*$', '', text_only).strip()

        # Check if this matches our target task
        if text_for_match != task_text:
            continue

        # Found the task! Now rewrite it
        task_found = True

        # Parse the original line to preserve all components
        original = line[6:].strip()  # Remove checkbox

        # Extract priority
        priority_match = re.match(r"^\*\*\[([^\]]+)\]\*\*\s*", original)
        priority = priority_match.group(1) if priority_match else "Med"

        # Remove priority tag from original
        remaining = re.sub(r"^\*\*\[[^\]]+\]\*\*\s*", "", original)

        # Remove status tag if present
        remaining = re.sub(r"^\*\*\[→\]\*\*\s*", "", remaining)

        # Now rebuild the line based on new_status
        if new_status == "Complete":
            new_line = f"- [x] **[{priority}]** {remaining}\n"
        elif new_status == "In Progress":
            new_line = f"- [ ] **[{priority}]** **[→]** {remaining}\n"
        else:  # New
            new_line = f"- [ ] **[{priority}]** {remaining}\n"

        lines[i] = new_line
        break

    if not task_found:
        return False

    # Write back
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return True


def append_task_to_section(section: str, task_line: str) -> bool:
    """
    Append task line to section in TASKS.md. Returns True on success.
    Example: append_task_to_section('Fundraising - Me', '- [ ] **[Hi]** Follow up with...')
    """
    path = os.path.join(PRODUCTIVITY_ROOT, "TASKS.md")
    if not os.path.exists(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    target = f"## {section}"
    inserted = False
    for i, ln in enumerate(lines):
        if ln.strip() == target:
            # Insert after section header
            lines.insert(i + 1, task_line + "\n")
            inserted = True
            break

    if not inserted:
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return True
