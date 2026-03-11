#!/usr/bin/env python3
"""
migrate_tasks_data_model.py — One-time migration for TASKS.md

Changes:
  - Strips **@Name** patterns, writes — assigned:Name inline field instead
  - Strips for:Name patterns, writes — assigned:Name inline field instead
  - Redistributes ## Waiting On tasks to ## Fundraising - Others or ## Other Work
  - Renames ## Work → ## Other Work
  - Merges ## Deals / Lending → ## Other Work
  - Drops empty sections (## IR / Fundraising, etc.)
  - Writes sections in canonical order

Backup: TASKS.md.bak.YYYYMMDD_HHMMSS (created before any writes)
"""

import os
import re
import shutil
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASKS_PATH = os.path.join(_PROJECT_ROOT, "TASKS.md")

FUNDRAISING_KEYWORDS = {
    'fund ii', 'fund 2', 'investor', 'lp', 'capital', 'commitment',
    'prospect', 'closing', 'irr', 'pitch', 'offering', 'mandate',
}

CANONICAL_SECTIONS = [
    'Fundraising - Me',
    'Fundraising - Others',
    'Other Work',
    'Personal',
    'Done',
]


def is_fundraising(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in FUNDRAISING_KEYWORDS)


def transform_task_line(line: str):
    """
    Parse a task line and convert it to new format.
    Strips **@Name** and for:Name patterns, appends — assigned:Name.
    Returns (new_line, mentions_count, for_count).
    """
    if not (line.startswith('- [ ] ') or line.startswith('- [x] ')):
        return line, 0, 0

    checkbox = line[:6]
    rest = line[6:].rstrip('\n')

    mentions_extracted = 0
    for_extracted = 0
    assigned_to = None

    # Extract **@Name** pattern
    om = re.search(r'\*\*@([^*]+)\*\*\s*', rest)
    if om:
        assigned_to = om.group(1).strip()
        rest = rest[:om.start()] + rest[om.end():]
        rest = rest.strip()
        mentions_extracted = 1

    # Extract for:Name tag from context
    fm = re.search(r'\s*—\s*for:\s*([^—\n]+)', rest)
    if fm:
        extracted_name = fm.group(1).strip()
        rest = rest[:fm.start()] + rest[fm.end():]
        rest = rest.strip()
        if assigned_to is None:
            assigned_to = extracted_name
        for_extracted = 1

    # Append — assigned:Name before any completion date
    if assigned_to and 'assigned:' not in rest:
        cdm = re.search(r'\s*—\s*completed\s+\d{4}-\d{2}-\d{2}', rest)
        if cdm:
            rest = rest[:cdm.start()] + f' — assigned:{assigned_to}' + rest[cdm.start():]
        else:
            rest = rest + f' — assigned:{assigned_to}'

    return checkbox + rest + '\n', mentions_extracted, for_extracted


def parse_sections(lines: list) -> dict:
    """Parse TASKS.md lines into {section_name: [task_lines]}."""
    sections = {}
    current = None
    current_lines = []

    def flush():
        if current is not None:
            sections[current] = current_lines[:]

    for line in lines:
        m = re.match(r'^## (.+)$', line.rstrip())
        if m:
            flush()
            current = m.group(1).strip()
            current_lines = []
        else:
            if current is not None:
                current_lines.append(line)

    flush()
    return sections


def count_tasks(lines: list) -> int:
    return sum(1 for l in lines if l.startswith('- [ ] ') or l.startswith('- [x] '))


def build_output(sections: dict) -> list:
    """Assemble final file lines in canonical section order."""
    out = ['# Tasks\n', '\n']
    for sec in CANONICAL_SECTIONS:
        task_lines = [l for l in sections.get(sec, []) if l.strip()]
        if not task_lines and sec != 'Done':
            continue
        out.append(f'## {sec}\n')
        out.extend(task_lines)
        out.append('\n')
    return out


def main():
    if not os.path.exists(TASKS_PATH):
        print(f"ERROR: TASKS.md not found at {TASKS_PATH}")
        return

    # Step 1: Backup
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'TASKS.md.bak.{ts}'
    backup_path = os.path.join(os.path.dirname(TASKS_PATH), backup_name)
    shutil.copy2(TASKS_PATH, backup_path)
    print(f"Backup: {backup_name}")

    with open(TASKS_PATH, 'r', encoding='utf-8') as f:
        raw_lines = f.readlines()

    # Step 2: Parse sections
    sections = parse_sections(raw_lines)

    # Step 3: Extract @mentions and for: tags from ALL sections
    total_mentions = 0
    total_for = 0
    transformed = {}
    for sec, sec_lines in sections.items():
        new_lines = []
        for line in sec_lines:
            cleaned, m, ft = transform_task_line(line)
            total_mentions += m
            total_for += ft
            new_lines.append(cleaned)
        transformed[sec] = new_lines

    # Step 4: Re-section Waiting On tasks
    waiting_tasks = transformed.pop('Waiting On', [])
    to_fundraising = []
    to_other_work = []
    to_done = []
    for line in waiting_tasks:
        if not line.strip():
            continue
        if line.startswith('- [x] '):
            to_done.append(line)
        elif line.startswith('- [ ] '):
            if is_fundraising(line):
                to_fundraising.append(line)
            else:
                to_other_work.append(line)

    # Step 5: Rename Work → Other Work, merge Deals/Lending → Other Work
    work_tasks = [l for l in transformed.pop('Work', []) if l.strip()]
    deals_tasks = [l for l in transformed.pop('Deals / Lending', []) if l.strip()]
    # Drop empty sections
    transformed.pop('IR / Fundraising', None)

    # Build final sections
    fundraising_me = [l for l in transformed.get('Fundraising - Me', []) if l.strip()]
    fundraising_others = to_fundraising
    other_work = work_tasks + deals_tasks + to_other_work
    personal = [l for l in transformed.get('Personal', []) if l.strip()]
    done_existing = [l for l in transformed.get('Done', []) if l.strip()]
    done = done_existing + to_done

    final_sections = {
        'Fundraising - Me': fundraising_me,
        'Fundraising - Others': fundraising_others,
        'Other Work': other_work,
        'Personal': personal,
        'Done': done,
    }

    # Step 6: Write back
    out = build_output(final_sections)
    with open(TASKS_PATH, 'w', encoding='utf-8') as f:
        f.writelines(out)

    # Step 7: Report
    total = sum(count_tasks(v) for v in final_sections.values())
    print(f"Migration complete.")
    print(f"  @mentions extracted:          {total_mentions}")
    print(f"  for: tags extracted:          {total_for}")
    print(f"  Waiting On → Fundraising:     {count_tasks(to_fundraising)}")
    print(f"  Waiting On → Other Work:      {count_tasks(to_other_work)}")
    print(f"  Waiting On → Done:            {count_tasks(to_done)}")
    print(f"  Deals / Lending → Other Work: {count_tasks(deals_tasks)}")
    print(f"  Work → Other Work:            {count_tasks(work_tasks)}")
    print(f"  Tasks written:                {total}")


if __name__ == '__main__':
    main()
