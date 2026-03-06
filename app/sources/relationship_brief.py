"""
relationship_brief.py — Aggregates knowledge base data for the CRM Relationship Brief.

Scans memory/people files, glossary, meeting summaries, and TASKS.md
to build a structured context object for any prospect org.

Also provides AI synthesis helpers: collect_relationship_data, build_context_block,
build_fallback_summary, merge_contacts_for_display, parse_intel_for_display.
"""

import os
import re
import json
import hashlib
from datetime import date


def _get_base_dir():
    """Resolve the ClaudeProductivity project root from this file's location."""
    # This file lives at app/sources/relationship_brief.py
    here = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(here)
    return os.path.dirname(app_dir)


def find_people_files(org_name, contact_names, base_dir=None):
    """
    Find memory/people/*.md files relevant to this org or any of its contacts.
    Matches by filename first, then by scanning file content.
    Returns list of {'filename': str, 'content': str}.
    """
    if base_dir is None:
        base_dir = _get_base_dir()

    people_dir = os.path.join(base_dir, "memory", "people")
    if not os.path.exists(people_dir):
        return []

    search_terms = [org_name.lower()] + [c.lower() for c in contact_names if c]
    matches = []

    for filename in sorted(os.listdir(people_dir)):
        if not filename.endswith('.md'):
            continue
        filepath = os.path.join(people_dir, filename)
        name_part = filename[:-3].replace('-', ' ').replace('_', ' ').lower()

        # Check filename first (fast path)
        matched = any(term in name_part or name_part in term for term in search_terms)

        # Fall back to scanning content
        if not matched:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content_lower = f.read().lower()
                matched = any(term in content_lower for term in search_terms)
            except OSError:
                continue

        if matched:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    matches.append({'filename': filename, 'content': f.read()})
            except OSError:
                pass

    return matches


def find_glossary_entry(org_name, base_dir=None):
    """
    Search memory/glossary.md for the org name and return surrounding context.
    Returns a string with matched sections separated by '---', or None.
    """
    if base_dir is None:
        base_dir = _get_base_dir()

    glossary_path = os.path.join(base_dir, "memory", "glossary.md")
    if not os.path.exists(glossary_path):
        return None

    try:
        with open(glossary_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        return None

    lines = content.split('\n')
    org_lower = org_name.lower()
    found_sections = []

    for i, line in enumerate(lines):
        if org_lower in line.lower():
            start = max(0, i - 5)
            end = min(len(lines), i + 11)
            found_sections.append('\n'.join(lines[start:end]))

    return '\n---\n'.join(found_sections) if found_sections else None


def find_meeting_summaries(org_name, contact_names, base_dir=None):
    """
    Find meeting summary files that reference this org or any of its contacts.
    Scans the meeting-summaries/ directory (YYYY-MM-DD prefixed markdown files).
    Returns list of {'filename': str, 'path': str, 'content': str}, newest first.
    """
    if base_dir is None:
        base_dir = _get_base_dir()

    meetings_dir = os.path.join(base_dir, "meeting-summaries")
    if not os.path.exists(meetings_dir):
        return []

    search_terms = [org_name.lower()] + [c.lower() for c in contact_names if c]
    matches = []

    for filename in os.listdir(meetings_dir):
        if not filename.endswith('.md'):
            continue
        filepath = os.path.join(meetings_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            if any(term in content.lower() for term in search_terms):
                matches.append({'filename': filename, 'path': filepath, 'content': content})
        except OSError:
            pass

    # Sort newest first (filenames are YYYY-MM-DD prefixed)
    matches.sort(key=lambda x: x['filename'], reverse=True)
    return matches


def find_org_tasks(org_name, contact_names, base_dir=None):
    """
    Find open tasks in TASKS.md that mention this org or any of its contacts.
    Returns list of task line strings (e.g. '- [ ] Follow up with Susannah Friar').
    """
    if base_dir is None:
        base_dir = _get_base_dir()

    tasks_path = os.path.join(base_dir, "TASKS.md")
    if not os.path.exists(tasks_path):
        return []

    try:
        with open(tasks_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        return []

    search_terms = [org_name.lower()] + [c.lower() for c in contact_names if c]
    tasks = []

    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped.startswith('- [ ]'):
            continue
        if any(term in stripped.lower() for term in search_terms):
            tasks.append(stripped)

    return tasks


# ---------------------------------------------------------------------------
# AI Synthesis Support
# ---------------------------------------------------------------------------

BRIEF_SYSTEM_PROMPT = """You are an AI analyst for a real estate private equity fund (AREC — Avila Real Estate Capital) currently raising a $1B debt fund (Fund II). You generate concise relationship intelligence briefs for the fundraising team.

Your audience is the COO who is actively managing LP relationships. He needs to know:
1. Where this prospect stands RIGHT NOW — stage, trajectory, momentum
2. What happened most recently — last meeting, last communication, last touch
3. Who the key people are and what their roles/dynamics are
4. What needs to happen next — pending tasks, upcoming meetings, open items
5. Any strategic context — prior AREC relationship, investor type nuances, decision-making process

RULES:
- Write in direct, professional prose. No headers, no bullet points, no markdown formatting.
- Write 2-4 short paragraphs. First paragraph = current status and recent momentum. Second = key relationships and contact dynamics. Third = next steps and open items. Fourth (optional) = strategic context if available.
- Be specific: use names, dates, dollar amounts, meeting details. Never be vague.
- If data is thin (few interactions, no meeting summaries), say so briefly and focus on what IS known. Do not pad with generic statements.
- Never invent information. Only use what is provided in the context.
- Omit any field that is empty or has no value. Never mention that a field is missing.
- Currency: use abbreviations ($50M, not $50,000,000).
- Refer to the fund as "Fund II" not "AREC Debt Fund II" in the narrative.
- When referencing AREC team members, use first names only (Oscar, Tony, James, Zach).
- Do not include a title or heading. Start directly with the narrative.
- Active tasks are displayed separately on the page below this brief. Do NOT enumerate or repeat them. Instead, reference next steps at a high level (e.g. "DD calls are scheduled for late March") without listing task text verbatim."""


def collect_relationship_data(org, offering, base_dir=None):
    """Collect all knowledge base data for an org/offering.
    Returns structured dict with all 8 sources."""
    from sources.crm_reader import (
        get_prospect, get_organization, get_contacts_for_org,
        load_interactions, get_emails_for_org,
    )

    if base_dir is None:
        base_dir = _get_base_dir()

    # Source 1: Prospect record
    prospect = get_prospect(org, offering) or {}

    # Source 2: Organization record
    organization = get_organization(org) or {}

    # Source 3: Contacts + people intel files
    contacts = get_contacts_for_org(org) or []
    contact_names = [c.get('name', '') for c in contacts]

    # Source 3b: memory/people/ intel files
    people_intel = find_people_files(org, contact_names, base_dir=base_dir)

    # Source 4: Interaction log
    interactions = load_interactions(org=org) or []

    # Source 5: Glossary entry
    glossary_entry = find_glossary_entry(org, base_dir=base_dir)

    # Source 6: Meeting summaries
    meeting_summaries = find_meeting_summaries(org, contact_names, base_dir=base_dir)

    # Source 7: Active tasks from TASKS.md
    active_tasks = find_org_tasks(org, contact_names, base_dir=base_dir)

    # Source 8: Email history
    email_history = get_emails_for_org(org) or []

    # Merged contacts for display (CRM + people intel)
    merged_contacts = merge_contacts_for_display(contacts, people_intel, org)

    return {
        'org_name': org,
        'offering': offering,
        'prospect': prospect,
        'organization': organization,
        'contacts': contacts,
        'people_intel': people_intel,
        'glossary_entry': glossary_entry,
        'interactions': interactions[:30],
        'meeting_summaries': meeting_summaries,
        'active_tasks': active_tasks,
        'email_history': email_history[:20],
        'merged_contacts': merged_contacts,
    }


def build_context_block(raw_data):
    """Build structured text context for the AI synthesis prompt.
    Only includes non-empty data. No empty fields."""

    sections = [f"TODAY'S DATE: {date.today().isoformat()}"]

    # Prospect record
    p = raw_data.get('prospect', {})
    if p:
        prospect_lines = []
        field_map = [
            ('Stage', 'Stage'), ('Target', 'Target'), ('Committed', 'Committed'),
            ('Closing', 'Closing'), ('Urgent', 'Urgent'), ('Assigned To', 'Assigned To'),
            ('Notes', 'Notes'), ('Last Touch', 'Last Touch'),
        ]
        for key, label in field_map:
            val = p.get(key, '')
            if val and str(val).strip() and str(val).strip().lower() not in ('false', 'none', '$0'):
                prospect_lines.append(f"- {label}: {val}")
        if prospect_lines:
            sections.append("PROSPECT RECORD:\n" + "\n".join(prospect_lines))

    # Organization
    org = raw_data.get('organization', {})
    if org:
        org_lines = []
        if org.get('type') or org.get('Type'):
            org_lines.append(f"- Type: {org.get('type') or org.get('Type')}")
        notes = org.get('notes') or org.get('Notes', '')
        if notes and str(notes).strip():
            org_lines.append(f"- Notes: {notes}")
        if org_lines:
            sections.append("ORGANIZATION:\n" + "\n".join(org_lines))

    # Contacts — only non-empty fields
    contacts = raw_data.get('contacts', [])
    if contacts:
        contact_lines = []
        for c in contacts:
            parts = [c.get('name', 'Unknown')]
            if c.get('title'):
                parts.append(c['title'])
            if c.get('email'):
                parts.append(c['email'])
            if c.get('role'):
                parts.append(f"Role: {c['role']}")
            if c.get('notes') and str(c['notes']).strip():
                parts.append(f"Notes: {c['notes']}")
            contact_lines.append(" | ".join(parts))
        sections.append("CONTACTS:\n" + "\n".join(f"- {cl}" for cl in contact_lines))

    # People intel files — full content
    people = raw_data.get('people_intel', [])
    if people:
        intel_parts = []
        for pf in people:
            content = pf.get('content', '').strip()
            if content:
                intel_parts.append(f"[{pf.get('filename', 'unknown')}]\n{content}")
        if intel_parts:
            sections.append("INTELLIGENCE FILES:\n" + "\n---\n".join(intel_parts))

    # Glossary
    glossary = raw_data.get('glossary_entry')
    if glossary and str(glossary).strip():
        sections.append("INVESTOR BACKGROUND (GLOSSARY):\n" + str(glossary).strip())

    # Interactions — compact format
    interactions = raw_data.get('interactions', [])
    if interactions:
        ix_lines = []
        for ix in interactions[:20]:
            parts = [ix.get('date', ''), ix.get('type', '')]
            if ix.get('contact'):
                parts.append(ix['contact'])
            summary = ix.get('summary') or ix.get('subject') or ''
            if summary:
                parts.append(summary)
            ix_lines.append(" — ".join(p for p in parts if p))
        if ix_lines:
            sections.append("INTERACTION HISTORY:\n" + "\n".join(f"- {il}" for il in ix_lines))

    # Meeting summaries — full content
    meetings = raw_data.get('meeting_summaries', [])
    if meetings:
        mtg_parts = []
        for ms in meetings:
            content = ms.get('content', '').strip()
            if content:
                mtg_parts.append(f"[{ms.get('filename', '')}]\n{content}")
        if mtg_parts:
            sections.append("MEETING SUMMARIES:\n" + "\n---\n".join(mtg_parts))

    # Active tasks
    tasks = raw_data.get('active_tasks', [])
    if tasks:
        sections.append("ACTIVE TASKS:\n" + "\n".join(f"- {t}" for t in tasks))

    # Email history
    emails = raw_data.get('email_history', [])
    if emails:
        email_lines = []
        for e in emails:
            parts = [e.get('date', ''), e.get('subject', ''), e.get('summary', '')]
            email_lines.append(" — ".join(p for p in parts if p))
        if email_lines:
            sections.append("EMAIL HISTORY:\n" + "\n".join(f"- {el}" for el in email_lines))

    return "\n\n".join(sections)


def build_fallback_summary(raw_data):
    """Fallback summary when AI synthesis is unavailable."""
    p = raw_data.get('prospect', {})
    parts = []

    stage = p.get('Stage', 'Unknown stage')
    target = p.get('Target', '')
    parts.append(
        f"{raw_data['org_name']} is at {stage}"
        + (f" targeting {target}" if target and target != '$0' else "")
        + "."
    )

    if p.get('Notes'):
        parts.append(p['Notes'])

    interactions = raw_data.get('interactions', [])
    if interactions:
        latest = interactions[0]
        summary = latest.get('summary') or latest.get('subject') or ''
        if summary:
            parts.append(f"Last interaction ({latest.get('date', '')}): {summary}")

    tasks = raw_data.get('active_tasks', [])
    if tasks:
        task_text = tasks[0].replace('- [ ] ', '').strip()
        # Strip markdown formatting
        task_text = re.sub(r'\*\*\[[^\]]+\]\*\*\s*', '', task_text)
        task_text = re.sub(r'\*\*@[^*]+\*\*\s*', '', task_text).strip()
        parts.append(
            f"Open task: {task_text}"
            + (f" (+{len(tasks)-1} more)" if len(tasks) > 1 else "")
        )

    return " ".join(parts)


def compute_content_hash(raw_data):
    """Compute a short MD5 hash of the raw data for cache invalidation."""
    return hashlib.md5(
        json.dumps(raw_data, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]


def merge_contacts_for_display(contacts, people_intel, org_name):
    """Merge CRM contacts with people intel files.
    Returns list of dicts with only non-empty fields."""

    # Index people intel by likely contact name match
    intel_by_name = {}
    for pf in people_intel:
        filename = pf.get('filename', '').replace('.md', '').replace('-', ' ').replace('_', ' ')
        matched = False
        for contact in contacts:
            cname = contact.get('name', '').lower()
            if cname and (cname in filename.lower() or filename.lower() in cname):
                intel_by_name[contact['name']] = pf.get('content', '')
                matched = True
                break
        if not matched and org_name.lower() in filename.lower():
            intel_by_name['_org_'] = pf.get('content', '')

    merged = []
    seen_names = set()

    for c in contacts:
        name = c.get('name', '').strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        entry = {'name': name}
        for field in ('title', 'email', 'phone', 'role', 'notes'):
            val = str(c.get(field, '') or '').strip()
            if val:
                entry[field] = val

        # Overlay intel from people files
        intel_content = intel_by_name.get(name)
        if intel_content:
            parsed = parse_intel_for_display(intel_content, org_name)
            for key, val in parsed.items():
                if val and key not in entry:
                    entry[key] = val

        merged.append(entry)

    return merged


def parse_intel_for_display(intel_content, org_name):
    """Extract display-worthy fields from a people intel markdown file.
    Skips redundant fields like Organization and Type."""

    result = {}
    skip_fields = {'organization', 'type', 'fund'}

    for line in intel_content.split('\n'):
        line = line.strip()
        if line.startswith('- **') or line.startswith('* **'):
            m = re.match(r'[-*]\s*\*\*(.+?):\*\*\s*(.*)', line)
            if m:
                field = m.group(1).strip().lower()
                value = m.group(2).strip()
                if field not in skip_fields and value:
                    result[field] = value

    return result


# ---------------------------------------------------------------------------
# Person Brief Support
# ---------------------------------------------------------------------------

PERSON_BRIEF_SYSTEM_PROMPT = """You are an AI analyst for a real estate private equity fund (AREC — Avila Real Estate Capital) currently raising a $1B debt fund (Fund II). You generate concise intelligence briefs about individual contacts and relationships.

Your audience is the COO who manages LP relationships. He needs to know:
1. Who this person IS — their role, seniority, decision-making authority within their organization
2. The RELATIONSHIP — how AREC has interacted with this person, who on the team has the relationship, communication style and preferences
3. Recent ACTIVITY — last interactions, what was discussed, any commitments or signals
4. CONTEXT — anything that helps prepare for the next conversation (personal details, preferences, past sticking points, what they care about)

RULES:
- Write in direct, professional prose. No headers, no bullet points, no markdown formatting.
- Write 2-3 short paragraphs. First = who they are and their role. Second = relationship history and recent activity. Third = strategic context and preparation notes.
- Be specific: use names, dates, meeting details. Never be vague.
- If data is thin, say so briefly and focus on what IS known. Do not pad.
- Never invent information. Only use what is provided in the context.
- Omit empty fields. Never mention that information is missing.
- Do NOT mention active tasks or to-do items. Tasks are displayed separately.
- Refer to AREC team by first names (Oscar, Tony, James, Zach).
- Refer to the fund as "Fund II" not "AREC Debt Fund II".
- Do not include a title or heading. Start directly with the narrative."""


PERSON_UPDATE_ROUTING_PROMPT = """You are a CRM data routing engine for a real estate private equity fund (AREC). The user is providing a free-text update about a specific person/contact. Determine exactly which data stores need to be updated.

Return ONLY valid JSON with no preamble:

{
  "contact_updates": [
    {"field": "email", "value": "new value"}
  ],
  "prospect_updates": [
    {"offering": "AREC Debt Fund II", "field": "notes", "value": "updated notes"}
  ],
  "interaction": {
    "type": "Call",
    "summary": "Brief summary"
  },
  "new_tasks": ["Task description"],
  "intel_notes": "New qualitative intelligence to append to this person's record"
}

RULES:
- Only include keys where the user's input implies a change. Omit keys with no update.
- contact_updates: for profile changes (email, phone, title, role)
- prospect_updates: if the update relates to a specific prospect/deal (stage change, notes)
- interaction: if a specific interaction occurred (call, meeting, email)
- new_tasks: if follow-up items are mentioned
- intel_notes: qualitative observations (communication style, preferences, relationship dynamics). Keep specific and factual.
- Return empty object {} if no data changes are warranted."""


def find_people_files_for_person(person_name, base_dir=None):
    """Find memory/people/ files for a specific person by name."""
    if base_dir is None:
        base_dir = _get_base_dir()

    people_dir = os.path.join(base_dir, "memory", "people")
    if not os.path.exists(people_dir):
        return []

    matches = []
    search_term = person_name.lower()

    for filename in os.listdir(people_dir):
        if not filename.endswith('.md'):
            continue
        name_part = filename[:-3].replace('-', ' ').replace('_', ' ').lower()
        if search_term in name_part or name_part in search_term:
            filepath = os.path.join(people_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    matches.append({'filename': filename, 'content': f.read()})
            except OSError:
                pass

    return matches


def find_meeting_summaries_for_person(person_name, org_name='', base_dir=None):
    """Find meeting summaries mentioning this person by name."""
    if base_dir is None:
        base_dir = _get_base_dir()

    meetings_dir = os.path.join(base_dir, "meeting-summaries")
    matches = []

    scan_dirs = [meetings_dir, os.path.join(meetings_dir, "archive")]
    for scan_dir in scan_dirs:
        if not os.path.exists(scan_dir):
            continue
        for filename in os.listdir(scan_dir):
            if not filename.endswith('.md'):
                continue
            filepath = os.path.join(scan_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if person_name.lower() in content.lower():
                    matches.append({'filename': filename, 'path': filepath, 'content': content})
            except OSError:
                pass

    matches.sort(key=lambda x: x['filename'], reverse=True)
    return matches


def get_email_history_for_person(email, org_name=''):
    """Get emails to/from a specific email address, filtered from org email log."""
    from sources.crm_reader import get_emails_for_org

    if not email or not org_name:
        return []

    try:
        all_emails = get_emails_for_org(org_name)
        em = email.lower()
        return [
            e for e in all_emails
            if em in (e.get('from', '') or '').lower()
            or em in ' '.join(e.get('to', []) or []).lower()
            or em in ' '.join(e.get('cc', []) or []).lower()
        ]
    except Exception:
        return []


def _build_person_profile(person_name, people_intel, org_name):
    """Build a profile dict from people intel files. Only non-empty fields."""
    profile = {'name': person_name}

    for pf in people_intel:
        content = pf.get('content', '')
        # Extract H1 name
        h1 = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        if h1:
            profile['name'] = h1.group(1).strip()
        # Extract field lines (with or without dash/asterisk prefix)
        for line in content.split('\n'):
            line = line.strip()
            m = re.match(r'(?:-|\*)?\s*\*\*(.+?):\*\*\s*(.*)', line)
            if not m:
                continue
            field = m.group(1).strip().lower()
            value = m.group(2).strip()
            if not value:
                continue
            if field in ('organization', 'org', 'company'):
                profile.setdefault('company', value)
            elif field in ('role', 'title'):
                profile.setdefault('title', value)
            elif field == 'email':
                profile.setdefault('email', value)
            elif field in ('phone', 'cell', 'mobile'):
                profile.setdefault('phone', value)

    if org_name:
        profile.setdefault('company', org_name)

    return profile


def collect_person_data(person_name, base_dir=None):
    """Collect all knowledge base data about a person across all sources."""
    from sources.crm_reader import (
        get_organization, get_prospects_for_org, load_interactions,
    )

    if base_dir is None:
        base_dir = _get_base_dir()

    # 1. People intel files
    people_intel = find_people_files_for_person(person_name, base_dir=base_dir)

    # 2. Extract org name from intel files
    org_name = ''
    for pf in people_intel:
        org_match = re.search(r'\*\*Organization:\*\*\s*(.+)', pf.get('content', ''))
        if org_match:
            org_name = org_match.group(1).strip()
            break

    # 3. Organization record
    organization = get_organization(org_name) if org_name else None

    # 4. Prospect connections
    prospects = get_prospects_for_org(org_name) if org_name else []

    # 5. Interactions — filter to this person; include all if they're primary contact
    all_interactions = load_interactions(org=org_name) if org_name else []
    person_interactions = [
        ix for ix in all_interactions
        if person_name.lower() in (ix.get('contact', '') or '').lower()
    ]
    is_primary = any(
        p.get('Primary Contact', '').lower() == person_name.lower()
        for p in prospects
    )
    if is_primary:
        person_interactions = all_interactions

    # 6. Glossary entry
    glossary_entry = find_glossary_entry(org_name, base_dir=base_dir) if org_name else None

    # 7. Meeting summaries mentioning this person
    meeting_summaries = find_meeting_summaries_for_person(person_name, org_name, base_dir=base_dir)

    # 8. Active tasks
    active_tasks = find_org_tasks(org_name, [person_name], base_dir=base_dir)

    # 9. Email
    profile = _build_person_profile(person_name, people_intel, org_name)
    email = profile.get('email', '')
    email_history = get_email_history_for_person(email, org_name) if email and org_name else []

    return {
        'name': person_name,
        'org_name': org_name,
        'profile': profile,
        'organization': organization or {},
        'prospects': prospects,
        'people_intel': people_intel,
        'glossary_entry': glossary_entry,
        'interactions': person_interactions[:30],
        'meeting_summaries': meeting_summaries,
        'active_tasks': active_tasks,
        'email_history': email_history,
        'email': email,
    }


def build_person_context_block(raw_data):
    """Build structured text context for the person brief AI prompt."""
    sections = [f"TODAY'S DATE: {date.today().isoformat()}"]

    profile = raw_data.get('profile', {})
    if profile:
        profile_lines = []
        for key in ('name', 'title', 'email', 'phone', 'organization'):
            val = str(profile.get(key, '') or '').strip()
            if val:
                profile_lines.append(f"- {key.title()}: {val}")
        if profile_lines:
            sections.append("PERSON PROFILE:\n" + "\n".join(profile_lines))

    org = raw_data.get('organization', {})
    if org:
        org_lines = []
        type_val = org.get('type') or org.get('Type', '')
        if type_val:
            org_lines.append(f"- Type: {type_val}")
        notes_val = org.get('notes') or org.get('Notes', '')
        if notes_val and str(notes_val).strip():
            org_lines.append(f"- Notes: {notes_val}")
        if org_lines:
            sections.append("ORGANIZATION:\n" + "\n".join(org_lines))

    prospects = raw_data.get('prospects', [])
    if prospects:
        person_name = raw_data.get('name', '')
        p_lines = []
        for p in prospects:
            parts = [p.get('offering', ''), p.get('Stage', '')]
            target = p.get('Target', '')
            if target and target != '$0':
                parts.append(target)
            if p.get('Primary Contact', '').lower() == person_name.lower():
                parts.append('(primary contact)')
            notes = p.get('Notes', '')
            if notes and str(notes).strip():
                parts.append(f"Notes: {notes}")
            assigned = p.get('Assigned To', '')
            if assigned:
                parts.append(f"Assigned: {assigned}")
            p_lines.append(" — ".join(pt for pt in parts if pt))
        sections.append("PROSPECT CONNECTIONS:\n" + "\n".join(f"- {pl}" for pl in p_lines))

    people_intel = raw_data.get('people_intel', [])
    for pf in people_intel:
        content = pf.get('content', '').strip()
        if content:
            sections.append(f"INTELLIGENCE FILE [{pf.get('filename', '')}]:\n{content}")

    glossary = raw_data.get('glossary_entry')
    if glossary and str(glossary).strip():
        sections.append("INVESTOR BACKGROUND:\n" + str(glossary).strip())

    interactions = raw_data.get('interactions', [])
    if interactions:
        ix_lines = []
        for ix in interactions[:20]:
            parts = [ix.get('date', ''), ix.get('type', '')]
            if ix.get('contact'):
                parts.append(ix['contact'])
            summary = ix.get('summary') or ix.get('subject') or ''
            if summary:
                parts.append(summary)
            ix_lines.append(" — ".join(p for p in parts if p))
        sections.append("INTERACTION HISTORY:\n" + "\n".join(f"- {il}" for il in ix_lines))

    meetings = raw_data.get('meeting_summaries', [])
    if meetings:
        mtg_parts = []
        for ms in meetings:
            content = ms.get('content', '').strip()
            if content:
                mtg_parts.append(f"[{ms.get('filename', '')}]\n{content}")
        if mtg_parts:
            sections.append("MEETING SUMMARIES:\n" + "\n---\n".join(mtg_parts))

    return "\n\n".join(sections)


def build_person_fallback_summary(raw_data):
    """Fallback when AI synthesis is unavailable."""
    parts = []
    profile = raw_data.get('profile', {})

    name = raw_data.get('name', 'Unknown')
    org = raw_data.get('org_name', '')
    title = str(profile.get('title', '') or '').strip()

    intro = name
    if title:
        intro += f" ({title})"
    if org:
        intro += f" at {org}"
    parts.append(intro + ".")

    prospects = raw_data.get('prospects', [])
    if prospects:
        p = prospects[0]
        offering = p.get('offering', '')
        stage = p.get('Stage', '')
        if offering and stage:
            parts.append(f"{offering} prospect at {stage}.")

    interactions = raw_data.get('interactions', [])
    if interactions:
        latest = interactions[0]
        summary = latest.get('summary') or latest.get('subject') or ''
        if summary:
            parts.append(f"Last interaction ({latest.get('date', '')}): {summary}")

    return " ".join(parts)


def execute_person_updates(person_name, org_name, updates, base_dir=None):
    """Execute AI-routed updates for a person record."""
    from sources.crm_reader import (
        update_contact_fields, get_prospects_for_org,
        update_prospect_field, append_interaction,
    )

    if base_dir is None:
        base_dir = _get_base_dir()

    results = []

    # Contact field updates
    for cu in updates.get('contact_updates', []):
        try:
            field = cu.get('field', '')
            value = cu.get('value', '')
            success = update_contact_fields(org_name, person_name, {field: value})
            results.append({
                'action': 'contact_update',
                'field': field,
                'status': 'success' if success else 'not_found',
            })
        except Exception as e:
            results.append({'action': 'contact_update', 'field': cu.get('field', ''), 'status': 'error', 'error': str(e)})

    # Prospect updates
    for pu in updates.get('prospect_updates', []):
        try:
            update_prospect_field(org_name, pu.get('offering', ''), pu['field'], pu['value'])
            results.append({'action': 'prospect_update', 'offering': pu.get('offering', ''), 'field': pu['field'], 'status': 'success'})
        except Exception as e:
            results.append({'action': 'prospect_update', 'status': 'error', 'error': str(e)})

    # Interaction
    interaction = updates.get('interaction')
    if interaction and org_name:
        try:
            entry = {
                'org': org_name,
                'offering': '',
                'type': interaction.get('type', 'Note'),
                'contact': person_name,
                'summary': interaction.get('summary', ''),
                'source': 'manual',
            }
            append_interaction(entry)
            # Update last_touch on all prospects for this org
            for p in get_prospects_for_org(org_name):
                update_prospect_field(org_name, p.get('offering', ''), 'last_touch', date.today().isoformat())
            results.append({'action': 'interaction', 'type': interaction.get('type'), 'status': 'success'})
        except Exception as e:
            results.append({'action': 'interaction', 'status': 'error', 'error': str(e)})

    # Intel notes → append to memory/people/ file
    intel_notes = updates.get('intel_notes')
    if intel_notes:
        try:
            append_person_intel(person_name, intel_notes, base_dir=base_dir)
            results.append({'action': 'intel_notes', 'status': 'success'})
        except Exception as e:
            results.append({'action': 'intel_notes', 'status': 'error', 'error': str(e)})

    # Tasks
    for task_text in updates.get('new_tasks', []):
        try:
            _append_task_to_md(task_text, org_name, base_dir=base_dir)
            results.append({'action': 'new_task', 'task': task_text, 'status': 'success'})
        except Exception as e:
            results.append({'action': 'new_task', 'status': 'error', 'error': str(e)})

    return results


def append_person_intel(person_name, notes, base_dir=None):
    """Append qualitative intel to a person's memory/people/ file. Creates file if needed."""
    if base_dir is None:
        base_dir = _get_base_dir()

    people_dir = os.path.join(base_dir, "memory", "people")
    os.makedirs(people_dir, exist_ok=True)

    slug = person_name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    filepath = os.path.join(people_dir, f"{slug}.md")

    today = date.today().isoformat()
    note_block = f"\n\n## {today}\n{notes}\n"

    if os.path.exists(filepath):
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(note_block)
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {person_name}\n{note_block}")


def _append_task_to_md(task_text, org_name, base_dir=None):
    """Append a new task line to TASKS.md under the Work section."""
    if base_dir is None:
        base_dir = _get_base_dir()

    tasks_path = os.path.join(base_dir, "TASKS.md")
    if not os.path.exists(tasks_path):
        return

    if org_name and org_name.lower() not in task_text.lower():
        task_line = f"- [ ] **[Med]** {task_text} ({org_name})\n"
    else:
        task_line = f"- [ ] **[Med]** {task_text}\n"

    with open(tasks_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, ln in enumerate(lines):
        if ln.strip() == '## Work':
            lines.insert(i + 1, task_line)
            break
    else:
        lines.append(f"\n## Work\n{task_line}")

    with open(tasks_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
