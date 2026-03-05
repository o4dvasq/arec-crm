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
        return {"fundraising": [], "personal": [], "waiting": [], "work": []}

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    tasks = {"fundraising": [], "personal": [], "waiting": [], "work": []}
    section_map = {
        "fundraising - me": "fundraising",
        "personal":         "personal",
        "waiting on":       "waiting",
        "work":             "work",
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
