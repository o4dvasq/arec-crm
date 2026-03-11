"""
memory_reader.py — Reads Dropbox markdown files for briefing injection (CC-05)
"""

import os
import re
from datetime import date

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app
PRODUCTIVITY_ROOT = os.path.dirname(_APP_ROOT)  # project root (works in any location)


# ---------------------------------------------------------------------------
# Task line parsing — shared by tasks_blueprint.py and update_task_status()
# ---------------------------------------------------------------------------

def _parse_task_line(line: str, section: str = '') -> dict:
    """Parse a single task markdown line into a dict."""
    line = line.rstrip()
    done = line.startswith('- [x] ')
    raw = line[6:].strip()
    text = raw

    # Priority
    priority = 'Med'
    pm = re.match(r'\*\*\[(\w+)\]\*\*\s*', text)
    if pm:
        priority = pm.group(1)
        text = text[pm.end():]

    # Status — based on checkbox and **[→]** marker
    if done:
        status = 'Complete'
    elif text.startswith('**[→]**'):
        status = 'In Progress'
        text = text[7:].strip()
    else:
        status = 'New'

    # Clean up old [STATUS:xxx] format for backward compatibility
    text = re.sub(r'\s*\[STATUS:\w+\]\s*', ' ', text).strip()

    # Completion date
    completion_date = None
    cdm = re.search(r'\s*—\s*completed\s+(\d{4}-\d{2}-\d{2})', text)
    if cdm:
        completion_date = cdm.group(1)
        text = text[:cdm.start()]

    # assigned:Name inline field
    assigned_to = None
    am = re.search(r'\s*—\s*assigned:([^—\n]+)', text)
    if am:
        assigned_to = am.group(1).strip()
        text = text[:am.start()] + text[am.end():]
        text = text.strip()

    # Fallback: legacy **@Name** format
    if assigned_to is None:
        om = re.match(r'\*\*@([^*]+)\*\*\s*', text)
        if om:
            assigned_to = om.group(1)
            text = text[om.end():]

    # (OrgName) suffix — filters out non-org parens like ($3M target)
    org = ''
    org_m = re.search(r'\(([^)]+)\)\s*$', text)
    if org_m:
        candidate = org_m.group(1).strip()
        if not re.match(r'^[\$\d]', candidate):
            org = candidate
            text = text[:org_m.start()].rstrip()

    # Context (after —)
    context = ''
    di = text.find(' — ')
    if di >= 0:
        context = text[di + 3:]
        text = text[:di]

    # Strip ~~strikethrough~~
    text = re.sub(r'~~(.+?)~~', r'\1', text)

    return {
        'text': text.strip(),
        'priority': priority,
        'status': status,
        'context': context,
        'assigned_to': assigned_to,
        'org': org,
        'complete': done,
        'completion_date': completion_date,
        'raw': raw,
    }


def _format_task_line(text: str, priority: str, context: str,
                      assigned_to: str, section: str, done: bool = False,
                      completion_date: str = None, status: str = 'New', org: str = '') -> str:
    """Serialize task fields back to a TASKS.md line."""
    checkbox = '- [x] ' if done else '- [ ] '
    line = f'**[{priority}]** '
    if status == 'In Progress' and not done:
        line += '**[→]** '
    line += text
    if org:
        line += f' ({org})'
    if context:
        line += f' — {context}'
    if assigned_to:
        line += f' — assigned:{assigned_to}'
    if done and completion_date:
        line += f' — completed {completion_date}'
    return checkbox + line + '\n'


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
        h2 = re.match(r"^## (.+)", line)
        if h2:
            current_section = h2.group(1).strip()
            continue

        if current_section != section:
            continue

        if not (line.startswith("- [ ] ") or line.startswith("- [x] ")):
            continue

        parsed = _parse_task_line(line, section)

        if parsed['text'] != task_text:
            continue

        task_found = True
        done = new_status == "Complete"
        lines[i] = _format_task_line(
            parsed['text'], parsed['priority'], parsed['context'],
            parsed['assigned_to'], section, done=done,
            completion_date=parsed['completion_date'],
            status=new_status, org=parsed.get('org', ''),
        )
        break

    if not task_found:
        return False

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
