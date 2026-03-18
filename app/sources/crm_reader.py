# crm_reader.py — markdown-file CRM backend. Single source of truth for all production code.
"""
CRM data reader/writer for all markdown files in crm/ and contacts/.
All downstream consumers import from here. No parsing logic elsewhere.
"""

import os
import re
import json
import uuid
from datetime import date, datetime, timedelta

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app
PROJECT_ROOT = os.path.dirname(APP_ROOT)  # .../ClaudeProductivity
CRM_ROOT = os.path.join(PROJECT_ROOT, "crm")
PEOPLE_ROOT = os.path.join(PROJECT_ROOT, "contacts")
TASKS_MD_PATH = os.path.join(PROJECT_ROOT, "TASKS.md")
BRIEFS_PATH = os.path.join(CRM_ROOT, "briefs.json")
PROSPECT_NOTES_PATH = os.path.join(CRM_ROOT, "prospect_notes.json")
PROSPECT_MEETINGS_PATH = os.path.join(CRM_ROOT, "prospect_meetings.json")
MEETINGS_PATH = os.path.join(CRM_ROOT, "meetings.json")

# Field write order for prospects
PROSPECT_FIELD_ORDER = [
    "Stage", "Target", "Primary Contact",
    "Closing", "Urgent", "Assigned To", "Notes", "Last Touch"
]

# Brief fields — appended after standard fields only when non-empty
BRIEF_FIELDS = ['Relationship Brief', 'Brief Refreshed']
BRIEF_FIELD_MAP = {
    'relationship brief': 'Relationship Brief',
    'brief refreshed': 'Brief Refreshed',
}

EDITABLE_FIELDS = {
    'stage', 'urgent', 'target', 'assigned_to',
    'notes', 'closing', 'primary_contact'
}


# ---------------------------------------------------------------------------
# Currency helpers
# ---------------------------------------------------------------------------

def _format_currency(n: float) -> str:
    """50000000 → '$50M', 1500000000 → '$1.5B'"""
    if n == 0:
        return "$0"
    if n >= 1_000_000_000:
        val = n / 1_000_000_000
        return f"${val:.2f}B"
    if n >= 1_000_000:
        val = n / 1_000_000
        formatted = f"{val:g}"
        return f"${formatted}M"
    if n >= 1_000:
        val = n / 1_000
        formatted = f"{val:g}"
        return f"${formatted}K"
    return f"${n:,.0f}"


def _parse_currency(s: str) -> float:
    """'$50,000,000' → 50000000.0, '$50M' → 50000000.0"""
    if not s or str(s).strip() in ('', '$0', '$'):
        return 0.0
    s = str(s).strip().replace(',', '').replace('$', '').strip()
    multipliers = {'B': 1_000_000_000, 'M': 1_000_000, 'K': 1_000}
    for suffix, mult in multipliers.items():
        if s.upper().endswith(suffix):
            try:
                return float(s[:-1]) * mult
            except ValueError:
                return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Low-level markdown helpers
# ---------------------------------------------------------------------------

def _read_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write_file(path: str, content: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def _parse_bullet_fields(lines: list[str]) -> dict:
    """Parse '- **Field:** value' lines into a dict.
    The format is '- **FieldName:** value' where the colon is inside the bold markers.
    """
    result = {}
    for line in lines:
        # Matches: - **Field Name:** value
        m = re.match(r'\s*-\s*\*\*(.+?):\*\*\s*(.*)', line)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            result[key] = value
    return result


def _fields_to_bullets(fields: dict, order: list[str]) -> list[str]:
    """Render a dict to ordered '- **Field:** value' lines."""
    lines = []
    seen = set()
    for key in order:
        # Case-insensitive lookup
        matched = next((k for k in fields if k.lower() == key.lower()), None)
        val = fields[matched] if matched else ''
        lines.append(f"- **{key}:** {val}")
        if matched:
            seen.add(matched)
    # Append any extras not in order
    for key, val in fields.items():
        if key not in seen:
            lines.append(f"- **{key}:** {val}")
    return lines


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_crm_config() -> dict:
    """Parse config.md into structured dict."""
    text = _read_file(os.path.join(CRM_ROOT, "config.md"))
    sections = {}
    current = None
    items = []
    for line in text.splitlines():
        heading = re.match(r'^## (.+)', line)
        if heading:
            if current:
                sections[current] = items
            current = heading.group(1).strip()
            items = []
        elif re.match(r'^\d+\. ', line):
            items.append(line.strip())
        elif re.match(r'^- ', line):
            items.append(line[2:].strip())
    if current:
        sections[current] = items

    # Parse team entries: "Full Name | email@domain.com" format
    raw_team = sections.get('AREC Team', [])
    team_list = []  # list of dicts: [{"name": "...", "email": "..."}]
    team_map = []   # list of {short, full, email} dicts for backward compat UI
    for entry in raw_team:
        if '|' in entry:
            name, email = [s.strip() for s in entry.split('|', 1)]
        else:
            name = entry.strip()
            email = ''  # backward compatible fallback

        short = name.split()[0]  # first name for short display
        team_list.append({'name': name, 'email': email})
        team_map.append({'short': short, 'full': name, 'email': email})

    return {
        'stages': sections.get('Pipeline Stages', []),
        'terminal_stages': sections.get('Terminal Stages', []),
        'org_types': sections.get('Organization Types', []),
        'closing_options': sections.get('Closing Options', []),
        'urgency_levels': sections.get('Urgency Levels', ['Yes']),
        'team': team_list,
        'team_map': team_map,
        'delegate_mailboxes': sections.get('Delegate Mailboxes', []),
    }


def get_team_member_email(name: str) -> str:
    """Look up email for an AREC team member by name. Returns empty string if not found.

    Case-insensitive match. Partial match OK (e.g., "James" matches "James Walton").
    Returns first match.
    """
    if not name:
        return ''

    config = load_crm_config()
    team = config.get('team', [])
    name_lower = name.lower().strip()

    # Try exact match first
    for member in team:
        if member['name'].lower() == name_lower:
            return member['email']

    # Try partial match (search for name in member name)
    for member in team:
        if name_lower in member['name'].lower():
            return member['email']

    return ''


# ---------------------------------------------------------------------------
# Offerings
# ---------------------------------------------------------------------------

def load_offerings() -> list[dict]:
    text = _read_file(os.path.join(CRM_ROOT, "offerings.md"))
    offerings = []
    current_name = None
    current_fields = []
    for line in text.splitlines():
        h2 = re.match(r'^## (.+)', line)
        if h2:
            if current_name:
                offerings.append({'name': current_name, **_parse_bullet_fields(current_fields)})
            current_name = h2.group(1).strip()
            current_fields = []
        elif line.strip().startswith('-') and current_name:
            current_fields.append(line)
    if current_name:
        offerings.append({'name': current_name, **_parse_bullet_fields(current_fields)})
    return offerings


def get_offering(name: str) -> dict | None:
    for o in load_offerings():
        if o['name'].lower() == name.lower():
            return o
    return None


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

def load_organizations() -> list[dict]:
    text = _read_file(os.path.join(CRM_ROOT, "organizations.md"))
    orgs = []
    current_name = None
    current_fields = []
    for line in text.splitlines():
        h2 = re.match(r'^## (.+)', line)
        if h2:
            if current_name is not None:
                orgs.append({'name': current_name, **_parse_bullet_fields(current_fields)})
            current_name = h2.group(1).strip()
            current_fields = []
        elif line.strip().startswith('-') and current_name is not None:
            current_fields.append(line)
    if current_name is not None:
        orgs.append({'name': current_name, **_parse_bullet_fields(current_fields)})
    return orgs


def get_organization(name: str) -> dict | None:
    for org in load_organizations():
        if org['name'].lower() == name.lower():
            return org
    return None


def write_organization(name: str, data: dict) -> None:
    """Update fields for an existing org. Preserves all fields."""
    # Canonical field order — any fields present in data are written in this
    # order first, then any remaining keys are appended alphabetically.
    _FIELD_ORDER = ['Type', 'Aliases', 'Domain', 'Contacts', 'Stage', 'Notes']

    path = os.path.join(CRM_ROOT, "organizations.md")
    text = _read_file(path)
    lines = text.splitlines()
    out = []
    i = 0
    updated = False
    while i < len(lines):
        line = lines[i]
        h2 = re.match(r'^## (.+)', line)
        if h2 and h2.group(1).strip().lower() == name.lower():
            out.append(line)
            i += 1
            # Collect existing bullet lines (may be multi-line notes with indentation)
            existing_bullets = []
            while i < len(lines) and (lines[i].strip().startswith('-') or lines[i].startswith('  ')):
                existing_bullets.append(lines[i])
                i += 1
            # Parse existing fields to preserve any not in data
            existing = _parse_bullet_fields(existing_bullets)
            merged = {**existing, **{k: v for k, v in data.items() if k != 'name'}}
            # Write in canonical order
            written = set()
            for key in _FIELD_ORDER:
                val = merged.get(key, '')
                if val or key in ('Type', 'Notes'):  # always write Type and Notes
                    out.append(f"- **{key}:** {val}")
                    written.add(key)
            # Any remaining keys not in canonical order
            for key in sorted(merged.keys()):
                if key not in written and key != 'name':
                    out.append(f"- **{key}:** {merged[key]}")
            # Blank line separator unless next is already blank or heading
            if i < len(lines) and lines[i].strip():
                out.append('')
            updated = True
        else:
            out.append(line)
            i += 1
    if not updated:
        # Org not found — append it
        out.append(f"\n## {name}")
        for key in _FIELD_ORDER:
            val = data.get(key, data.get(key.lower(), ''))
            if val or key in ('Type', 'Notes'):
                out.append(f"- **{key}:** {val}")
    _write_file(path, '\n'.join(out))


def delete_organization(name: str) -> None:
    """Remove org section from organizations.md."""
    path = os.path.join(CRM_ROOT, "organizations.md")
    text = _read_file(path)
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        h2 = re.match(r'^## (.+)', line)
        if h2 and h2.group(1).strip().lower() == name.lower():
            i += 1
            # Skip the section content
            while i < len(lines) and not re.match(r'^## ', lines[i]):
                i += 1
        else:
            out.append(line)
            i += 1
    _write_file(path, '\n'.join(out))


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

def load_contacts_index() -> dict:
    """Returns {org_name: [slug, ...]}

    Supports two formats:
      Flat:    - Org Name: slug-a, slug-b
      Headed:  ## Org Name\\n- slug-a\\n- slug-b
    """
    path = os.path.join(CRM_ROOT, "contacts_index.md")
    if not os.path.exists(path):
        return {}
    text = _read_file(path)
    result = {}
    current_org = None
    for line in text.splitlines():
        h2 = re.match(r'^## (.+)', line)
        if h2:
            current_org = h2.group(1).strip()
            result[current_org] = []
        # Flat format: "- Org Name: slug-a, slug-b"
        elif re.match(r'^- .+:', line):
            parts = line[2:].split(':', 1)
            org = parts[0].strip()
            slugs = [s.strip() for s in parts[1].split(',') if s.strip()]
            result.setdefault(org, []).extend(slugs)
            current_org = None  # reset so bare "- slug" lines don't attach here
        elif re.match(r'^- ', line) and current_org:
            slug = line[2:].strip()
            if slug:
                result[current_org].append(slug)
    return result


def load_person(slug: str) -> dict | None:
    """Parse a contacts/<slug>.md file into a dict."""
    path = os.path.join(PEOPLE_ROOT, f"{slug}.md")
    if not os.path.exists(path):
        return None
    text = _read_file(path)
    lines = text.splitlines()
    person = {'slug': slug, 'name': '', 'organization': '', 'role': '',
              'email': '', 'phone': '', 'type': ''}
    # First H1 = name
    for line in lines:
        if line.startswith('# '):
            person['name'] = line[2:].strip()
            break
    # Look for Overview section (- **Field:** value)
    in_overview = False
    for line in lines:
        if re.match(r'^## Overview', line):
            in_overview = True
            continue
        if in_overview and re.match(r'^## ', line):
            break
        if in_overview:
            m = re.match(r'\s*-?\s*\*\*(.+?):\*\*\s*(.*)', line)
            if m:
                key = m.group(1).strip().lower()
                val = m.group(2).strip()
                if key == 'organization':
                    person['organization'] = val
                elif key == 'role':
                    person['role'] = val
                elif key == 'email':
                    person['email'] = val
                elif key == 'phone':
                    person['phone'] = val
                elif key == 'type':
                    person['type'] = val
    # Fallback for older non-Overview format: **Field:** value at top level
    if not person['organization']:
        for line in lines:
            m = re.match(r'\s*-?\s*\*\*(.+?):\*\*\s*(.*)', line)
            if m:
                key = m.group(1).strip().lower()
                val = m.group(2).strip()
                if key == 'organization':
                    person['organization'] = val
                elif key in ('role', 'title'):
                    person['role'] = val
                elif key == 'email':
                    person['email'] = val
                elif key == 'phone':
                    person['phone'] = val
    return person


def get_contacts_for_org(org_name: str) -> list[dict]:
    """Return list of person dicts for all contacts linked to this org."""
    index = load_contacts_index()
    contacts = []
    # Case-insensitive match
    for indexed_org, slugs in index.items():
        # Strip disambiguator for matching: "UTIMCO (Jared Brimberry)" → "UTIMCO"
        base_org = re.sub(r'\s*\([^)]+\)\s*$', '', indexed_org).strip()
        if base_org.lower() == org_name.lower() or indexed_org.lower() == org_name.lower():
            for slug in slugs:
                person = load_person(slug)
                if person:
                    contacts.append(person)
    return contacts


def find_person_by_email(email: str) -> dict | None:
    """Search all person files for a matching email."""
    if not os.path.exists(PEOPLE_ROOT):
        return None
    for filename in os.listdir(PEOPLE_ROOT):
        if not filename.endswith('.md'):
            continue
        slug = filename[:-3]
        person = load_person(slug)
        if person and person.get('email', '').lower() == email.lower():
            return person
    return None


def _name_to_slug(name: str) -> str:
    """Convert 'Susannah Friar' → 'susannah-friar'"""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def create_person_file(name: str, org: str, email: str, role: str, person_type: str) -> str:
    """Create contacts/<slug>.md and update contacts_index.md. Returns slug."""
    slug = _name_to_slug(name)
    # Ensure unique slug
    base_slug = slug
    counter = 2
    while os.path.exists(os.path.join(PEOPLE_ROOT, f"{slug}.md")):
        slug = f"{base_slug}-{counter}"
        counter += 1

    os.makedirs(PEOPLE_ROOT, exist_ok=True)
    content = f"# {name}\n\n## Overview\n"
    content += f"- **Organization:** {org}\n"
    content += f"- **Role:** {role}\n"
    content += f"- **Email:** {email}\n"
    content += f"- **Phone:** \n"
    content += f"- **Type:** {person_type}\n"
    _write_file(os.path.join(PEOPLE_ROOT, f"{slug}.md"), content)

    # Update contacts_index.md
    index_path = os.path.join(CRM_ROOT, "contacts_index.md")
    if os.path.exists(index_path):
        text = _read_file(index_path)
    else:
        text = "# Contacts Index\n"

    lines = text.splitlines()
    # Find the org heading
    org_found = False
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        h2 = re.match(r'^## (.+)', line)
        if h2 and h2.group(1).strip().lower() == org.lower():
            out.append(line)
            i += 1
            # Add all existing slugs
            while i < len(lines) and (lines[i].startswith('-') or lines[i].strip() == ''):
                out.append(lines[i])
                i += 1
            out.append(f"- {slug}")
            org_found = True
        else:
            out.append(line)
            i += 1

    if not org_found:
        out.append(f"\n## {org}\n- {slug}")

    _write_file(index_path, '\n'.join(out))
    return slug


def load_all_persons() -> list[dict]:
    """Load all person files from contacts/. Returns list of person dicts sorted by name."""
    if not os.path.exists(PEOPLE_ROOT):
        return []
    persons = []
    for filename in sorted(os.listdir(PEOPLE_ROOT)):
        if not filename.endswith('.md'):
            continue
        slug = filename[:-3]
        person = load_person(slug)
        if person and person.get('name'):
            persons.append(person)
    persons.sort(key=lambda p: p['name'].lower())
    return persons


def enrich_person_email(slug: str, email: str) -> None:
    """Update the Email field in a person's file."""
    path = os.path.join(PEOPLE_ROOT, f"{slug}.md")
    if not os.path.exists(path):
        return
    text = _read_file(path)
    if re.search(r'\*\*Email:\*\*', text):
        text = re.sub(r'(\*\*Email:\*\*)\s*.*', rf'\1 {email}', text)
    else:
        text += f"\n- **Email:** {email}\n"
    _write_file(path, text)


def add_contact_to_index(org: str, slug: str) -> None:
    """Add a slug under an org in contacts_index.md, deduplicating. Creates the org section if absent."""
    index_path = os.path.join(CRM_ROOT, "contacts_index.md")
    if os.path.exists(index_path):
        text = _read_file(index_path)
    else:
        text = "# Contacts Index\n"

    # Check if slug already present
    index = load_contacts_index()
    for indexed_org, slugs in index.items():
        if indexed_org.lower() == org.lower() and slug in slugs:
            return  # already indexed

    lines = text.splitlines()
    org_found = False
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        h2 = re.match(r'^## (.+)', line)
        if h2 and h2.group(1).strip().lower() == org.lower():
            out.append(line)
            i += 1
            while i < len(lines) and (lines[i].startswith('-') or lines[i].strip() == ''):
                out.append(lines[i])
                i += 1
            out.append(f"- {slug}")
            org_found = True
        else:
            out.append(line)
            i += 1

    if not org_found:
        out.append(f"\n## {org}\n- {slug}")

    _write_file(index_path, '\n'.join(out))

    # Auto-set Primary Contact on this org's prospects if none is set
    _auto_set_primary_contact_for_org(org, slug)


def _auto_set_primary_contact_for_org(org: str, slug: str) -> None:
    """If this org's prospects have no Primary Contact, set the newly added contact as primary."""
    person = load_person(slug)
    if not person:
        return
    name = person.get('name', '')
    if not name:
        return
    prospects = get_prospects_for_org(org)
    for prospect in prospects:
        if not prospect.get('Primary Contact', '').strip():
            update_prospect_field(prospect['org'], prospect['offering'], 'Primary Contact', name)


def ensure_contact_linked(name: str, org: str) -> None:
    """Ensure a Primary Contact name is linked to its org in contacts_index.
    Creates the person file if it doesn't exist. Idempotent."""
    if not name or not org:
        return
    slug = _name_to_slug(name)
    if not slug:
        return
    # Check if slug already in the index for this org
    index = load_contacts_index()
    for indexed_org, slugs in index.items():
        base_org = re.sub(r'\s*\([^)]+\)\s*$', '', indexed_org).strip()
        if base_org.lower() == org.lower() or indexed_org.lower() == org.lower():
            if slug in slugs:
                return  # already linked
    # Create person file if it doesn't exist
    person_path = os.path.join(PEOPLE_ROOT, f"{slug}.md")
    if not os.path.exists(person_path):
        os.makedirs(PEOPLE_ROOT, exist_ok=True)
        content = f"# {name}\n\n## Overview\n"
        content += f"- **Organization:** {org}\n"
        content += f"- **Role:** \n"
        content += f"- **Email:** \n"
        content += f"- **Phone:** \n"
        content += f"- **Type:** investor\n"
        _write_file(person_path, content)
    # Add to contacts index
    add_contact_to_index(org, slug)


def update_contact_fields(org: str, name: str, fields: dict) -> bool:
    """Update editable fields on a contact person file. Returns True on success."""
    # Find slug via contacts_index
    index = load_contacts_index()
    slug = None
    for indexed_org, slugs in index.items():
        base_org = re.sub(r'\s*\([^)]+\)\s*$', '', indexed_org).strip()
        if base_org.lower() == org.lower() or indexed_org.lower() == org.lower():
            for s in slugs:
                person = load_person(s)
                if person and person.get('name', '').lower() == name.lower():
                    slug = s
                    break
    if not slug:
        # Try direct slug match
        slug = _name_to_slug(name)

    path = os.path.join(PEOPLE_ROOT, f"{slug}.md")
    if not os.path.exists(path):
        return False

    text = _read_file(path)
    field_map = {
        'role': 'Role', 'email': 'Email', 'phone': 'Phone', 'title': 'Role'
    }
    for field_key, field_label in field_map.items():
        if field_key in fields:
            val = fields[field_key]
            pattern = rf'(\*\*{field_label}:\*\*)\s*.*'
            replacement = rf'\1 {val}'
            if re.search(pattern, text):
                text = re.sub(pattern, replacement, text)
            else:
                # Add to Overview section
                text = re.sub(
                    r'(## Overview\n)',
                    rf'\1- **{field_label}:** {val}\n',
                    text
                )
    _write_file(path, text)
    return True


# ---------------------------------------------------------------------------
# Prospects
# ---------------------------------------------------------------------------

def _parse_prospect_heading(heading: str) -> tuple[str, str | None]:
    """
    '### Merseyside Pension Fund' → ('Merseyside Pension Fund', None)
    '### UTIMCO (Jared Brimberry)' → ('UTIMCO', 'Jared Brimberry')
    """
    m = re.match(r'### (.+?)\s*\((.+)\)\s*$', heading)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m2 = re.match(r'### (.+)', heading)
    if m2:
        return m2.group(1).strip(), None
    return heading, None


def load_prospects(offering: str = None) -> list[dict]:
    """Load all prospects, optionally filtered by offering name."""
    text = _read_file(os.path.join(CRM_ROOT, "prospects.md"))
    prospects = []
    current_offering = None
    current_org = None
    current_disambig = None
    current_fields = []

    def flush():
        if current_org and current_offering:
            fields = _parse_bullet_fields(current_fields)
            prospects.append({
                'org': current_org,
                'disambiguator': current_disambig,
                'offering': current_offering,
                **fields,
            })

    for line in text.splitlines():
        h2 = re.match(r'^## (.+)', line)
        h3 = re.match(r'^### (.+)', line)
        if h2:
            flush()
            current_offering = h2.group(1).strip()
            current_org = None
            current_disambig = None
            current_fields = []
        elif h3:
            flush()
            org, disambig = _parse_prospect_heading(line)
            current_org = org
            current_disambig = disambig
            current_fields = []
        elif line.strip().startswith('-') and current_org:
            current_fields.append(line)
    flush()

    if offering:
        prospects = [p for p in prospects if p['offering'].lower() == offering.lower()]
    # Normalize boolean urgent field
    for p in prospects:
        p['urgent'] = p.get('Urgent', '').lower() == 'yes'
    return prospects


def get_prospect(org: str, offering: str) -> dict | None:
    for p in load_prospects(offering):
        if p['org'].lower() == org.lower():
            return p
    return None


def get_prospects_for_org(org: str) -> list[dict]:
    """Return all prospects for this org across all offerings."""
    return [p for p in load_prospects() if p['org'].lower() == org.lower()]


def write_prospect(org: str, offering: str, data: dict) -> None:
    """Write or create a prospect record. Preserves ordering."""
    path = os.path.join(CRM_ROOT, "prospects.md")
    text = _read_file(path)
    lines = text.splitlines()
    out = []
    i = 0
    current_offering = None
    prospect_written = False

    def make_prospect_block(org_name: str, fields: dict) -> list[str]:
        block = [f"### {org_name}"]
        for key in PROSPECT_FIELD_ORDER:
            # Case-insensitive lookup
            matched = next((k for k in fields if k.lower() == key.lower()), None)
            val = fields[matched] if matched else ''
            # Enforce single string for Assigned To — take first name before semicolon
            if key.lower() == 'assigned to' and ';' in str(val):
                val = str(val).split(';')[0].strip()
            block.append(f"- **{key}:** {val}")
        # Append brief fields only when non-empty (optional, no blank lines added)
        for key in BRIEF_FIELDS:
            matched = next((k for k in fields if k.lower() == key.lower()), None)
            val = (fields[matched] if matched else '').strip()
            if val:
                block.append(f"- **{key}:** {val}")
        return block

    while i < len(lines):
        line = lines[i]
        h2 = re.match(r'^## (.+)', line)
        h3 = re.match(r'^### (.+)', line)

        if h2:
            current_offering = h2.group(1).strip()
            out.append(line)
            i += 1
        elif h3 and current_offering and current_offering.lower() == offering.lower():
            heading_org, _ = _parse_prospect_heading(line)
            if heading_org.lower() == org.lower():
                # Replace this block
                for block_line in make_prospect_block(heading_org, data):
                    out.append(block_line)
                i += 1
                # Skip old field lines
                while i < len(lines) and lines[i].strip().startswith('-'):
                    i += 1
                prospect_written = True
            else:
                out.append(line)
                i += 1
        else:
            out.append(line)
            i += 1

    if not prospect_written:
        # Append under the correct offering
        new_block = make_prospect_block(org, data)
        new_lines = []
        found_offering = False
        for idx, line in enumerate(out):
            new_lines.append(line)
            if re.match(r'^## (.+)', line) and line[3:].strip().lower() == offering.lower():
                found_offering = True
        if found_offering:
            # Insert before next H2 or at end
            final = []
            inserted = False
            in_target = False
            for line in new_lines:
                h2m = re.match(r'^## (.+)', line)
                if h2m and h2m.group(1).strip().lower() == offering.lower():
                    in_target = True
                    final.append(line)
                elif in_target and h2m and not inserted:
                    final.extend(new_block)
                    final.append('')
                    final.append(line)
                    inserted = True
                    in_target = False
                else:
                    final.append(line)
            if not inserted:
                final.append('')
                final.extend(new_block)
            out = final
        else:
            # Create the offering section
            out.append(f"\n## {offering}")
            out.extend(new_block)

    _write_file(path, '\n'.join(out))


def delete_prospect(org: str, offering: str) -> None:
    path = os.path.join(CRM_ROOT, "prospects.md")
    text = _read_file(path)
    lines = text.splitlines()
    out = []
    i = 0
    current_offering = None
    while i < len(lines):
        line = lines[i]
        h2 = re.match(r'^## (.+)', line)
        h3 = re.match(r'^### (.+)', line)
        if h2:
            current_offering = h2.group(1).strip()
            out.append(line)
            i += 1
        elif h3 and current_offering and current_offering.lower() == offering.lower():
            heading_org, _ = _parse_prospect_heading(line)
            if heading_org.lower() == org.lower():
                i += 1
                while i < len(lines) and lines[i].strip().startswith('-'):
                    i += 1
            else:
                out.append(line)
                i += 1
        else:
            out.append(line)
            i += 1
    _write_file(path, '\n'.join(out))


def update_prospect_field(org: str, offering: str, field: str, value: str) -> None:
    """Update a single field on a prospect. Also auto-updates Last Touch.
    Accepts field names with underscores or spaces, case-insensitive.
    """
    prospect = get_prospect(org, offering)
    if prospect is None:
        return
    # Normalize: 'assigned_to' → 'assigned to' for case-insensitive match
    field_normalized = field.lower().replace('_', ' ')
    # Reject next_action — field has been removed from the data model
    if field_normalized == 'next action':
        return
    # Normalize urgent: True/False/boolean-string → "Yes" or ""
    if field_normalized == 'urgent':
        value = 'Yes' if str(value).lower() in ('yes', 'true', '1') else ''
    # Enforce single string for assigned_to
    if field_normalized == 'assigned to' and ';' in str(value):
        value = str(value).split(';')[0].strip()
    field_title = next(
        (k for k in PROSPECT_FIELD_ORDER if k.lower() == field_normalized),
        BRIEF_FIELD_MAP.get(field_normalized, field)
    )
    prospect[field_title] = value
    # Auto-update last touch (skip for brief fields — they're not relationship touches)
    if field_normalized not in BRIEF_FIELD_MAP:
        prospect['Last Touch'] = date.today().isoformat()
    write_prospect(org, offering, prospect)
    # Auto-link contact to org when Primary Contact is set
    if field_normalized == 'primary contact' and value:
        ensure_contact_linked(value, org)


# ---------------------------------------------------------------------------
# Pipeline summaries
# ---------------------------------------------------------------------------

def get_fund_summary(offering: str) -> dict:
    prospects = load_prospects(offering)
    config = load_crm_config()
    excluded = set(config['terminal_stages'] + ['0. Not Pursuing'])
    active = [p for p in prospects if p.get('Stage', '') not in excluded]

    total_target = sum(_parse_currency(p.get('Target', '0')) for p in active)

    # Committed = sum of Targets from stages 6. Verbal + 7. Legal / DD + 8. Closed
    committed_stages = {'6. Verbal', '7. Legal / DD', '8. Closed'}
    total_committed = sum(
        _parse_currency(p.get('Target', '0'))
        for p in prospects
        if p.get('Stage', '') in committed_stages
    )

    offering_data = get_offering(offering) or {}
    fund_target = _parse_currency(offering_data.get('Target', '0'))

    return {
        'offering': offering,
        'prospect_count': len(active),
        'total_target': total_target,
        'total_target_fmt': _format_currency(total_target),
        'total_committed': total_committed,
        'total_committed_fmt': _format_currency(total_committed),
        'fund_target': fund_target,
        'fund_target_fmt': _format_currency(fund_target),
    }


def get_fund_summary_all() -> list[dict]:
    return [get_fund_summary(o['name']) for o in load_offerings()]


def get_pipeline_summary(offering: str) -> dict:
    """Stage-by-stage breakdown."""
    prospects = load_prospects(offering)
    by_stage = {}
    for p in prospects:
        stage = p.get('Stage', '')
        by_stage.setdefault(stage, {'count': 0, 'target': 0.0})
        by_stage[stage]['count'] += 1
        by_stage[stage]['target'] += _parse_currency(p.get('Target', '0'))
    return by_stage


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------

def load_interactions(org: str = None, offering: str = None, limit: int = None) -> list[dict]:
    path = os.path.join(CRM_ROOT, "interactions.md")
    if not os.path.exists(path):
        return []
    text = _read_file(path)
    interactions = []
    current_date = ''
    current_heading = None
    current_fields = []

    def flush():
        if current_heading and current_date:
            # Parse "Org — Type — Offering"
            parts = [p.strip() for p in current_heading.split(' — ')]
            entry_org = parts[0] if len(parts) > 0 else ''
            entry_type = parts[1] if len(parts) > 1 else ''
            entry_offering = parts[2] if len(parts) > 2 else ''
            fields = _parse_bullet_fields(current_fields)
            interactions.append({
                'date': current_date,
                'org': entry_org,
                'type': entry_type,
                'offering': entry_offering,
                **fields,
            })

    for line in text.splitlines():
        h2 = re.match(r'^## (.+)', line)
        h3 = re.match(r'^### (.+)', line)
        if h2:
            flush()
            current_date = h2.group(1).strip()
            current_heading = None
            current_fields = []
        elif h3:
            flush()
            current_heading = h3.group(1).strip()
            current_fields = []
        elif line.strip().startswith('-') and current_heading:
            current_fields.append(line)
    flush()

    if org:
        interactions = [i for i in interactions if i['org'].lower() == org.lower()]
    if offering:
        interactions = [i for i in interactions if i['offering'].lower() == offering.lower()]
    # Sort newest first
    interactions.sort(key=lambda x: x.get('date', ''), reverse=True)
    if limit:
        interactions = interactions[:limit]
    return interactions


def append_interaction(entry: dict) -> None:
    """Append an interaction entry. Also updates prospect last_touch."""
    path = os.path.join(CRM_ROOT, "interactions.md")
    today = date.today().isoformat()
    entry_date = entry.get('date', today)

    heading = f"### {entry.get('org', '')} — {entry.get('type', '')} — {entry.get('offering', '')}"
    fields = []
    for key in ('Contact', 'Subject', 'Summary', 'Source'):
        val = entry.get(key, entry.get(key.lower(), ''))
        fields.append(f"- **{key}:** {val}")

    if os.path.exists(path):
        text = _read_file(path)
    else:
        text = "# Interaction Log\n"

    date_pattern = f"## {entry_date}"
    if date_pattern in text:
        # Insert under the existing date heading
        text = text.replace(date_pattern, f"{date_pattern}\n\n{heading}\n" + '\n'.join(fields))
    else:
        text = text.rstrip() + f"\n\n## {entry_date}\n\n{heading}\n" + '\n'.join(fields) + "\n"

    _write_file(path, text)

    # Update last_touch on the associated prospect
    if entry.get('org') and entry.get('offering'):
        update_prospect_field(entry['org'], entry['offering'], 'Last Touch', today)


# ---------------------------------------------------------------------------
# Cross-reference
# ---------------------------------------------------------------------------

def get_prospect_full(org: str, offering: str) -> dict | None:
    prospect = get_prospect(org, offering)
    if not prospect:
        return None
    org_data = get_organization(org) or {}
    contacts = get_contacts_for_org(org)
    return {**prospect, **{f'org_{k}': v for k, v in org_data.items() if k != 'name'}, 'contacts': contacts}


def resolve_primary_contact(org: str, contact_name: str) -> dict | None:
    for person in get_contacts_for_org(org):
        if person.get('name', '').lower() == contact_name.lower():
            return person
    return None


# ---------------------------------------------------------------------------
# Pending Interviews
# ---------------------------------------------------------------------------

def load_pending_interviews() -> list[dict]:
    path = os.path.join(CRM_ROOT, "pending_interviews.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get('pending', [])


def add_pending_interview(entry: dict) -> None:
    path = os.path.join(CRM_ROOT, "pending_interviews.json")
    pending = load_pending_interviews()
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    # Purge old entries
    pending = [p for p in pending if p.get('detected_at', '') >= cutoff]
    # Dedup by org
    pending = [p for p in pending if p.get('org', '').lower() != entry.get('org', '').lower()]
    pending.append(entry)
    with open(path, 'w') as f:
        json.dump({'pending': pending}, f, indent=2)


def remove_pending_interview(org: str) -> None:
    path = os.path.join(CRM_ROOT, "pending_interviews.json")
    pending = load_pending_interviews()
    pending = [p for p in pending if p.get('org', '').lower() != org.lower()]
    with open(path, 'w') as f:
        json.dump({'pending': pending}, f, indent=2)


# ---------------------------------------------------------------------------
# Unmatched Review
# ---------------------------------------------------------------------------

def load_unmatched() -> list[dict]:
    path = os.path.join(CRM_ROOT, "unmatched_review.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get('items', [])


def add_unmatched(item: dict) -> None:
    path = os.path.join(CRM_ROOT, "unmatched_review.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    else:
        data = {'items': []}
    items = data.get('items', [])
    # Dedup by email
    email = item.get('participant_email', '').lower()
    items = [i for i in items if i.get('participant_email', '').lower() != email]
    items.append(item)
    data['items'] = items
    data['last_scan'] = datetime.now().isoformat()[:19]
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def remove_unmatched(email: str) -> None:
    path = os.path.join(CRM_ROOT, "unmatched_review.json")
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)
    data['items'] = [i for i in data.get('items', [])
                     if i.get('participant_email', '').lower() != email.lower()]
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def purge_old_unmatched(days: int = 14) -> None:
    path = os.path.join(CRM_ROOT, "unmatched_review.json")
    if not os.path.exists(path):
        return
    with open(path) as f:
        data = json.load(f)
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    data['items'] = [i for i in data.get('items', []) if i.get('date', '') >= cutoff]
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Tasks (from TASKS.md)
# ---------------------------------------------------------------------------

def load_tasks_by_org() -> dict[str, list[dict]]:
    """Parse TASKS.md and return open tasks grouped by org name.

    Returns: { 'UTIMCO': [{'task': '...', 'owner': 'Oscar', 'section': 'Fundraising - Me', 'index': 3, 'priority': 'Hi'}, ...], ... }

    Tasks are matched to orgs via the (OrgName) suffix convention.
    Only open tasks (unchecked) from all sections are included.
    Each task includes its section name and 0-based index within that section,
    matching the Tasks API indexing for edit/delete operations.
    """
    tasks_path = os.path.join(PROJECT_ROOT, "TASKS.md")
    if not os.path.exists(tasks_path):
        return {}

    text = _read_file(tasks_path)
    result: dict[str, list[dict]] = {}
    current_section = None
    task_index = 0  # 0-based index within current section

    for line in text.splitlines():
        stripped = line.strip()

        # Track which section we're in
        if stripped.startswith('## '):
            current_section = stripped[3:].strip()
            task_index = 0  # Reset index for each section
            continue

        # Skip Personal and Done sections
        if current_section in ('Personal', 'Done', None):
            continue

        # Count ALL tasks (open and done) for correct indexing
        if stripped.startswith('- [ ]') or stripped.startswith('- [x]'):
            if stripped.startswith('- [x]'):
                task_index += 1
                continue  # Skip done tasks but count them

            # Only process open (unchecked) tasks
            # Extract priority: **[Hi]** etc
            pri_match = re.search(r'\*\*\[(\w+)\]\*\*', stripped)
            priority = pri_match.group(1) if pri_match else 'Med'

            # Extract owner: prefer **@Name**, fall back to — assigned:Name
            owner_match = re.search(r'\*\*@([^*]+)\*\*', stripped)
            if owner_match:
                owner = owner_match.group(1).strip()
            else:
                assigned_match = re.search(r'—\s*assigned:(.+)$', stripped)
                owner = assigned_match.group(1).strip() if assigned_match else 'Oscar'

            # Extract org: (OrgName) at end of line, optionally followed by — assigned:...
            org_match = re.search(r'\(([^)]+)\)\s*(?:—\s*assigned:[^)]*)?$', stripped)
            if not org_match:
                task_index += 1
                continue  # Not a CRM task

            org_name = org_match.group(1).strip()

            # Extract task description: strip checkbox, priority, owner tag, and trailing (OrgName)
            desc = stripped
            desc = re.sub(r'^- \[ \]\s*\*\*\[\w+\]\*\*\s*', '', desc)  # Remove checkbox + priority
            desc = re.sub(r'\*\*@[^*]+\*\*\s*', '', desc)               # Remove owner tag (supports multi-word names)
            desc = re.sub(r'\s*—\s*assigned:.*$', '', desc)              # Remove — assigned:Person suffix
            desc = re.sub(r'\s*\([^)]+\)\s*$', '', desc)                # Remove trailing (OrgName)
            desc = desc.strip(' —-')                                     # Clean up leftover separators

            result.setdefault(org_name, []).append({
                'task': desc,
                'owner': owner,
                'section': current_section,
                'index': task_index,
                'priority': priority,
            })

            task_index += 1

    return result


# ---------------------------------------------------------------------------
# Prospect Tasks (TASKS.md — [org: OrgName] tag format)
# ---------------------------------------------------------------------------

def _parse_org_tagged_task(line: str, section: str) -> dict | None:
    """Parse a TASKS.md line with [org: ...] tag. Returns None if no org tag."""
    stripped = line.strip()
    if not (stripped.startswith('- [ ]') or stripped.startswith('- [x]')):
        return None
    org_m = re.search(r'\[org:\s*([^\]]+)\]', stripped)
    if not org_m:
        return None
    org_name = org_m.group(1).strip()
    status = 'done' if stripped.startswith('- [x]') else 'open'
    pri_m = re.search(r'\*\*\[(\w+)\]\*\*', stripped)
    priority = pri_m.group(1) if pri_m else 'Med'
    owner_m = re.search(r'\[owner:\s*([^\]]+)\]', stripped)
    owner = owner_m.group(1).strip() if owner_m else ''
    # Build clean text: strip checkbox, priority tag, [org:] and [owner:] tags
    text = re.sub(r'^- \[.\]\s*', '', stripped)
    text = re.sub(r'\*\*\[\w+\]\*\*\s*', '', text)
    text = re.sub(r'\[org:\s*[^\]]+\]', '', text)
    text = re.sub(r'\[owner:\s*[^\]]+\]', '', text)
    text = text.strip(' —-').strip()
    return {
        'org': org_name,
        'text': text,
        'owner': owner,
        'priority': priority,
        'status': status,
        'section': section,
        'raw_line': stripped,
    }


def get_tasks_for_prospect(org_name: str) -> list[dict]:
    """Scan TASKS.md for tasks tagged [org: org_name]. Case-insensitive."""
    if not os.path.exists(TASKS_MD_PATH):
        return []
    results = []
    current_section = None
    org_lower = org_name.lower()
    for line in _read_file(TASKS_MD_PATH).splitlines():
        stripped = line.strip()
        if stripped.startswith('## '):
            current_section = stripped[3:].strip()
            continue
        if current_section:
            task = _parse_org_tagged_task(line, current_section)
            if task and task['org'].lower() == org_lower:
                results.append({k: v for k, v in task.items() if k != 'org'})
    return results


def get_all_prospect_tasks() -> list[dict]:
    """Scan TASKS.md for all tasks tagged with any [org: ...] tag."""
    if not os.path.exists(TASKS_MD_PATH):
        return []
    results = []
    current_section = None
    for line in _read_file(TASKS_MD_PATH).splitlines():
        stripped = line.strip()
        if stripped.startswith('## '):
            current_section = stripped[3:].strip()
            continue
        if current_section:
            task = _parse_org_tagged_task(line, current_section)
            if task:
                results.append(task)
    return results


def add_prospect_task(org_name: str, text: str, owner: str,
                      priority: str = "Med", section: str = "IR / Fundraising") -> bool:
    """Append a new prospect task to TASKS.md under the specified section.
    Format: - [ ] **[{priority}]** {text} — [org: {org_name}] [owner: {owner}]
    Returns True on success.
    """
    if not org_name or not text or not owner:
        return False
    if not os.path.exists(TASKS_MD_PATH):
        return False
    new_line = f'- [ ] **[{priority}]** {text} — [org: {org_name}] [owner: {owner}]\n'
    with open(TASKS_MD_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    target = f'## {section}'
    inserted = False
    for i, ln in enumerate(lines):
        if ln.strip() == target:
            lines.insert(i + 1, new_line)
            inserted = True
            break
    if not inserted:
        lines.append(f'\n## {section}\n')
        lines.append(new_line)
    with open(TASKS_MD_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    return True


def complete_prospect_task(org_name: str, task_text: str) -> bool:
    """Find open task matching org_name + partial text, mark it done.
    Returns True if found and updated.
    """
    if not os.path.exists(TASKS_MD_PATH):
        return False
    with open(TASKS_MD_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    org_lower = org_name.lower()
    text_lower = task_text.lower().strip()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith('- [ ]'):
            continue
        org_m = re.search(r'\[org:\s*([^\]]+)\]', stripped)
        if org_m:
            if org_m.group(1).strip().lower() != org_lower:
                continue
        else:
            # Legacy format: no [org:] tag — match by org name appearing in task text
            if org_lower not in stripped.lower():
                continue
        if text_lower in stripped.lower():
            lines[i] = line.replace('- [ ]', '- [x]', 1)
            with open(TASKS_MD_PATH, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
    return False


# ---------------------------------------------------------------------------
# Meeting History
# ---------------------------------------------------------------------------

MEETING_HISTORY_PATH = os.path.join(CRM_ROOT, 'meeting_history.md')


def load_meeting_history(org: str) -> list[dict]:
    """Return list of {date, title, attendees, source, notion_url} for an org."""
    if not os.path.exists(MEETING_HISTORY_PATH):
        return []

    text = _read_file(MEETING_HISTORY_PATH)
    in_section = False
    results = []

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith('## '):
            in_section = (stripped[3:].strip().lower() == org.lower())
            continue

        if not in_section or not stripped.startswith('- '):
            continue

        # Format: - **YYYY-MM-DD** | Title | Attendees | Source
        parts = stripped[2:].split(' | ')
        date_m = re.match(r'\*\*([^*]+)\*\*', parts[0].strip())
        date = date_m.group(1) if date_m else parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ''
        attendees = parts[2].strip() if len(parts) > 2 else ''
        source_raw = parts[3].strip() if len(parts) > 3 else ''
        notion_url_m = re.search(r'\[Notion\]\(([^)]+)\)', source_raw)
        notion_url = notion_url_m.group(1) if notion_url_m else ''

        results.append({
            'date': date,
            'title': title,
            'attendees': attendees,
            'source': source_raw,
            'notion_url': notion_url,
        })

    return results


def add_meeting_entry(org: str, date: str, title: str, attendees: str, source: str, notion_url: str = '') -> None:
    """Append a meeting entry under the org's ## section. Creates section if missing. Deduplicates by date+title."""
    # Deduplicate
    for m in load_meeting_history(org):
        if m['date'] == date and m['title'].lower() == title.lower():
            return

    # Build source string
    if notion_url and source == 'calendar':
        source_str = f'calendar + [Notion]({notion_url})'
    elif notion_url:
        source_str = f'[Notion]({notion_url})'
    else:
        source_str = source or 'manual'

    entry_line = f'- **{date}** | {title} | {attendees} | {source_str}'

    if os.path.exists(MEETING_HISTORY_PATH):
        text = _read_file(MEETING_HISTORY_PATH)
    else:
        text = '# Meeting History\n'

    lines = text.splitlines()

    # Find org's ## section
    section_line = None
    for i, line in enumerate(lines):
        if line.strip() == f'## {org}':
            section_line = i
            break

    if section_line is None:
        # Append new section at end
        if lines and lines[-1].strip():
            lines.append('')
        lines.append(f'## {org}')
        lines.append(entry_line)
    else:
        # Insert before the next ## section (or at end of file)
        insert_pos = section_line + 1
        while insert_pos < len(lines) and not lines[insert_pos].startswith('## '):
            insert_pos += 1
        lines.insert(insert_pos, entry_line)

    _write_file(MEETING_HISTORY_PATH, '\n'.join(lines) + '\n')


# ---------------------------------------------------------------------------
# Email Log (crm/email_log.json)
# ---------------------------------------------------------------------------

EMAIL_LOG_PATH = os.path.join(CRM_ROOT, "email_log.json")

# Domains to exclude from matching (internal AREC + generic providers)
_INTERNAL_DOMAINS = {"avilacapllc.com", "avilacapital.com", "builderadvisorgroup.com"}
_GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "me.com", "live.com", "msn.com", "protonmail.com",
    "mail.com", "zoho.com",
}
# Service providers — orgs we work with but are NOT investor prospects.
# Email scan should only target orgs that have active prospects in the pipeline.
_SERVICE_PROVIDER_ORGS = {
    "Clifford Chance",      # external legal counsel
    "South40 Capital",      # placement agent (UK/Europe)
    "Greshler Finance",     # placement agent (Israel)
    "First Forte",          # placement agent (Middle East)
    "Maples",               # Cayman legal/admin
}


def load_email_log() -> dict:
    """Load email_log.json. Returns structure with 'emails' list."""
    if not os.path.exists(EMAIL_LOG_PATH):
        return {"version": 1, "lastScan": None, "emails": []}
    with open(EMAIL_LOG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_email_log(data: dict) -> None:
    """Atomically write email_log.json."""
    with open(EMAIL_LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_email_by_message_id(message_id: str) -> dict | None:
    """Return email entry from log or None."""
    log = load_email_log()
    for email in log.get('emails', []):
        if email.get('messageId') == message_id:
            return email
    return None


def get_emails_for_org(org_name: str) -> list[dict]:
    """Return all emails matching an org, sorted descending by date."""
    log = load_email_log()
    org_lower = org_name.lower()
    matched = [
        e for e in log.get('emails', [])
        if e.get('orgMatch', '').lower() == org_lower
    ]
    matched.sort(key=lambda e: e.get('timestamp', ''), reverse=True)
    return matched


def add_emails_to_log(emails: list[dict]) -> int:
    """Append emails to log, deduplicating by messageId. Returns count added."""
    log = load_email_log()
    existing_ids = {e.get('messageId') for e in log.get('emails', [])}
    added = 0
    for email in emails:
        mid = email.get('messageId')
        if mid and mid not in existing_ids:
            log['emails'].append(email)
            existing_ids.add(mid)
            added += 1
    log['lastScan'] = datetime.now().isoformat() + 'Z'
    save_email_log(log)
    return added


def get_emails_for_org_grouped(org_name: str) -> list[dict]:
    """Return emails for an org grouped by conversationId.

    Returns a list of thread dicts, each containing:
      - conversationId: str | None
      - emails: list[dict] (sorted newest first)
      - count: int
      - latest_date: str
      - latest_subject: str
      - latest_direction: str
      - latest_mailbox_source: str

    Threads sorted by most recent email date, descending.
    Emails with no conversationId appear as single-email threads.
    """
    emails = get_emails_for_org(org_name)

    thread_map: dict[str, list] = {}
    ungrouped: list[dict] = []

    for email in emails:
        cid = email.get("conversationId")
        if cid:
            if cid not in thread_map:
                thread_map[cid] = []
            thread_map[cid].append(email)
        else:
            ungrouped.append(email)

    threads = []
    for cid, thread_emails in thread_map.items():
        thread_emails.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        latest = thread_emails[0]
        threads.append({
            "conversationId": cid,
            "emails": thread_emails,
            "count": len(thread_emails),
            "latest_date": latest.get("date", ""),
            "latest_subject": latest.get("subject", ""),
            "latest_direction": latest.get("direction", ""),
            "latest_mailbox_source": latest.get("mailboxSource", ""),
        })

    for email in ungrouped:
        threads.append({
            "conversationId": None,
            "emails": [email],
            "count": 1,
            "latest_date": email.get("date", ""),
            "latest_subject": email.get("subject", ""),
            "latest_direction": email.get("direction", ""),
            "latest_mailbox_source": email.get("mailboxSource", ""),
        })

    threads.sort(key=lambda t: t["latest_date"], reverse=True)
    return threads


def get_org_domains(prospect_only: bool = False) -> dict:
    """Return map of org name -> domain (e.g. 'NEPC' -> 'nepc.com').
    Extracted from the Domain field in organizations.md.
    If prospect_only=True, only returns orgs that have active prospects
    and excludes service providers (law firms, placement agents, etc.)."""
    # Build the set of org names that have prospects (if filtering)
    prospect_org_names = set()
    if prospect_only:
        for p in load_prospects():
            prospect_org_names.add(p.get('org', '').strip())

    domains = {}
    for org in load_organizations():
        org_name = org['name']
        # Skip service providers
        if org_name in _SERVICE_PROVIDER_ORGS:
            continue
        # If prospect_only, skip orgs without active prospects
        if prospect_only and org_name not in prospect_org_names:
            continue
        domain = org.get('Domain', '').strip()
        if domain:
            # Normalize: remove leading @ if present
            domain = domain.lstrip('@').lower()
            if domain and domain not in _GENERIC_DOMAINS:
                domains[org_name] = domain
    return domains


def get_org_by_domain(domain: str) -> str | None:
    """Reverse lookup: domain string -> org name, or None.
    Excludes service providers."""
    domain = domain.lower().lstrip('@')
    if domain in _INTERNAL_DOMAINS or domain in _GENERIC_DOMAINS:
        return None
    # Use unfiltered domains for matching (so inbound from any known org still resolves)
    # but skip service providers
    org_domains = get_org_domains(prospect_only=False)
    for org_name, org_domain in org_domains.items():
        if org_domain == domain:
            return org_name
    return None


# ---------------------------------------------------------------------------
# Email enrichment helpers
# ---------------------------------------------------------------------------

def enrich_org_domain(org_name: str, domain: str) -> bool:
    """Add Domain field to an org if it doesn't already have one.
    Skips generic/internal domains. Returns True if org was updated."""
    if not org_name or not domain:
        return False
    domain = domain.lower().lstrip('@')
    if domain in _GENERIC_DOMAINS or domain in _INTERNAL_DOMAINS:
        return False
    org = get_organization(org_name)
    if not org:
        return False
    existing_domain = org.get('Domain', '').strip().lstrip('@').lower()
    if existing_domain:
        return False  # already has a domain
    write_organization(org_name, {'Domain': f'@{domain}'})
    return True


def append_person_email_history(slug: str, date_str: str, subject: str,
                                 direction: str) -> None:
    """Append a compact entry to ## Email History section on a person file.
    Creates the section if it doesn't exist. Deduplicates by (date, subject)."""
    path = os.path.join(PEOPLE_ROOT, f"{slug}.md")
    if not os.path.exists(path):
        return
    text = _read_file(path)
    entry = f"- {date_str}: {subject} ({direction})"
    # Check for existing Email History section
    if '## Email History' in text:
        # Check for duplicate
        if entry in text:
            return
        # Insert after section header (before next ## or end of file)
        lines = text.splitlines()
        out = []
        inserted = False
        for i, line in enumerate(lines):
            out.append(line)
            if line.strip() == '## Email History' and not inserted:
                out.append(entry)
                inserted = True
        _write_file(path, '\n'.join(out))
    else:
        # Append new section
        if not text.endswith('\n'):
            text += '\n'
        text += f"\n## Email History\n{entry}\n"
        _write_file(path, text)


def append_org_email_history(org_name: str, date_str: str, subject: str,
                              contact: str, direction: str) -> None:
    """Append a compact entry to ## Email History inside the org's section
    in organizations.md. Creates the subsection if needed. Deduplicates."""
    path = os.path.join(CRM_ROOT, "organizations.md")
    if not os.path.exists(path):
        return
    text = _read_file(path)
    lines = text.splitlines()

    tag = f"  - {date_str}: {subject} — {contact} ({direction})"
    if tag in text:
        return  # already recorded

    out = []
    i = 0
    updated = False
    while i < len(lines):
        line = lines[i]
        h2 = re.match(r'^## (.+)', line)
        if h2 and h2.group(1).strip().lower() == org_name.lower():
            out.append(line)
            i += 1
            # Walk through bullet fields and existing content
            history_found = False
            while i < len(lines) and not re.match(r'^## ', lines[i]):
                out.append(lines[i])
                if lines[i].strip() == '- **Email History:**':
                    history_found = True
                    # Insert right after the header line
                    out.append(tag)
                    updated = True
                i += 1
            if not history_found:
                # Add Email History field before the trailing blank lines
                # Remove trailing blank lines from this section
                while out and out[-1].strip() == '':
                    out.pop()
                out.append('- **Email History:**')
                out.append(tag)
                out.append('')  # blank separator
                updated = True
        else:
            out.append(line)
            i += 1

    if updated:
        _write_file(path, '\n'.join(out))


def discover_and_enrich_contact_emails(
    org_name: str,
    email_addresses: list[tuple[str, str]]
) -> dict:
    """Given a list of (email, display_name) seen in emails for an org,
    try to match them to existing contacts and enrich their Email field.
    Also discovers the org domain if missing.

    Returns {'domain_added': bool, 'emails_enriched': int, 'details': [...]}.
    """
    result = {'domain_added': False, 'emails_enriched': 0, 'details': []}
    if not org_name or not email_addresses:
        return result

    # (a) Try to set org domain from the first non-generic external email
    for email_addr, _ in email_addresses:
        if not email_addr:
            continue
        domain = email_addr.split('@')[-1].lower()
        if domain not in _GENERIC_DOMAINS and domain not in _INTERNAL_DOMAINS:
            if enrich_org_domain(org_name, domain):
                result['domain_added'] = True
                result['details'].append(f"Added domain @{domain} to {org_name}")
            break  # only try domain from first external address

    # (c) For each email address, see if it belongs to a known contact at this org
    contacts = get_contacts_for_org(org_name)
    # Get the org's domain for matching
    org = get_organization(org_name)
    org_domain = (org.get('Domain', '') if org else '').strip().lstrip('@').lower()

    for email_addr, display_name in email_addresses:
        if not email_addr:
            continue
        email_lower = email_addr.lower()
        addr_domain = email_lower.split('@')[-1]

        # Skip internal/generic
        if addr_domain in _INTERNAL_DOMAINS or addr_domain in _GENERIC_DOMAINS:
            continue

        # Only process if email domain matches org domain
        if org_domain and addr_domain != org_domain:
            continue

        # Check if any contact at this org is missing an email — try name match
        already_has = find_person_by_email(email_addr)
        if already_has:
            continue  # someone already has this email

        # Try to match by name to a contact without email
        for contact in contacts:
            if contact.get('email'):
                continue  # already has email
            contact_name = contact.get('name', '').lower()
            display_lower = display_name.lower().strip()
            if not contact_name or not display_lower:
                continue
            # Match: display name contains contact's first or last name,
            # or contact name contains display name
            name_parts = contact_name.split()
            if any(part in display_lower for part in name_parts if len(part) >= 3):
                enrich_person_email(contact['slug'], email_addr)
                result['emails_enriched'] += 1
                result['details'].append(
                    f"Set email {email_addr} on {contact.get('name', contact['slug'])}"
                )
                break  # one match per email address

    return result


# ---------------------------------------------------------------------------
# Brief persistence (server-side AI brief cache)
# ---------------------------------------------------------------------------

def _load_briefs() -> dict:
    """Load briefs.json. Returns {'prospect': {...}, 'person': {...}, 'org': {...}}."""
    if not os.path.exists(BRIEFS_PATH):
        return {'prospect': {}, 'person': {}, 'org': {}}
    with open(BRIEFS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_briefs(data: dict) -> None:
    """Atomically write briefs.json."""
    os.makedirs(os.path.dirname(BRIEFS_PATH), exist_ok=True)
    with open(BRIEFS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_brief(brief_type: str, key: str, narrative: str, content_hash: str,
               at_a_glance: str = '') -> None:
    """Persist an AI-generated brief.

    Args:
        brief_type: 'prospect', 'person', or 'org'
        key: unique identifier — for prospect use '{org}::{offering}',
             for person use slug or name, for org use org name.
        narrative: the AI-generated markdown text
        content_hash: hash of the source data at generation time
        at_a_glance: optional 10-word-max status line (prospect briefs only)
    """
    data = _load_briefs()
    bucket = data.setdefault(brief_type, {})
    existing = bucket.get(key, {})
    bucket[key] = {
        'narrative': narrative,
        'content_hash': content_hash,
        'generated_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        # Preserve existing at_a_glance if no new one provided (auto-synthesis path)
        'at_a_glance': at_a_glance if at_a_glance else existing.get('at_a_glance', ''),
    }
    _save_briefs(data)


def load_saved_brief(brief_type: str, key: str) -> dict | None:
    """Return saved brief dict {'narrative', 'content_hash', 'generated_at', 'at_a_glance'} or None."""
    data = _load_briefs()
    return data.get(brief_type, {}).get(key)


def load_all_briefs() -> dict:
    """Return the full briefs.json dict (all types). Used by pipeline API."""
    return _load_briefs()


# ---------------------------------------------------------------------------
# Prospect Notes Log
# ---------------------------------------------------------------------------

def load_prospect_notes(org: str, offering: str) -> list:
    """Load the freeform notes log for a prospect.
    Returns list of {'date': ISO str, 'author': str, 'text': str}, oldest first."""
    key = f"{org}::{offering}"
    if not os.path.exists(PROSPECT_NOTES_PATH):
        return []
    try:
        with open(PROSPECT_NOTES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get(key, [])
    except (json.JSONDecodeError, OSError):
        return []


def save_prospect_note(org: str, offering: str, author: str, text: str) -> dict:
    """Append a timestamped note entry to a prospect's notes log.
    Returns the new entry dict {'date', 'author', 'text'}."""
    key = f"{org}::{offering}"
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    entry = {
        'date': now,
        'author': author.strip(),
        'text': text.strip(),
    }

    data: dict = {}
    if os.path.exists(PROSPECT_NOTES_PATH):
        try:
            with open(PROSPECT_NOTES_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    data.setdefault(key, []).append(entry)

    os.makedirs(os.path.dirname(PROSPECT_NOTES_PATH), exist_ok=True)
    with open(PROSPECT_NOTES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return entry


# ---------------------------------------------------------------------------
# Prospect Upcoming Meetings
# ---------------------------------------------------------------------------

def load_prospect_meetings(org: str, offering: str) -> list:
    """Load upcoming meetings for a prospect.
    Returns list of dicts sorted by meeting_date ascending."""
    key = f"{org}::{offering}"
    if not os.path.exists(PROSPECT_MEETINGS_PATH):
        return []
    try:
        with open(PROSPECT_MEETINGS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        entries = data.get(key, [])
        return sorted(entries, key=lambda e: e.get('meeting_date', ''))
    except (json.JSONDecodeError, OSError):
        return []


def save_prospect_meeting(org: str, offering: str, meeting_date: str,
                          meeting_time: str, attendees: str, purpose: str) -> dict:
    """Append an upcoming meeting entry for a prospect.
    Returns the new entry dict."""
    key = f"{org}::{offering}"
    created_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    entry = {
        'id': created_at,  # unique enough for deletion
        'meeting_date': meeting_date.strip(),
        'meeting_time': meeting_time.strip(),
        'attendees': attendees.strip(),
        'purpose': purpose.strip(),
        'created_at': created_at,
    }

    data: dict = {}
    if os.path.exists(PROSPECT_MEETINGS_PATH):
        try:
            with open(PROSPECT_MEETINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    data.setdefault(key, []).append(entry)

    os.makedirs(os.path.dirname(PROSPECT_MEETINGS_PATH), exist_ok=True)
    with open(PROSPECT_MEETINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return entry


def delete_prospect_meeting(org: str, offering: str, meeting_id: str) -> bool:
    """Remove an upcoming meeting entry by its id. Returns True if found and removed."""
    key = f"{org}::{offering}"
    if not os.path.exists(PROSPECT_MEETINGS_PATH):
        return False
    try:
        with open(PROSPECT_MEETINGS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    entries = data.get(key, [])
    new_entries = [e for e in entries if e.get('id') != meeting_id]
    if len(new_entries) == len(entries):
        return False

    data[key] = new_entries
    with open(PROSPECT_MEETINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True


# ---------------------------------------------------------------------------
# Meetings — First-Class Object (unified meetings.json)
# ---------------------------------------------------------------------------

MEETING_STATUSES = ('scheduled', 'completed', 'reviewed')
MEETING_SOURCES = ('calendar', 'email', 'manual')


def _load_meetings_raw() -> list:
    """Load all meetings from meetings.json. Returns list of dicts."""
    if not os.path.exists(MEETINGS_PATH):
        return []
    try:
        with open(MEETINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_meetings_raw(meetings: list) -> None:
    """Write all meetings to meetings.json."""
    os.makedirs(os.path.dirname(MEETINGS_PATH), exist_ok=True)
    with open(MEETINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(meetings, f, indent=2, ensure_ascii=False)


def load_meetings(org: str = None, offering: str = None,
                  status: str | list = None,
                  future_only: bool = False, past_only: bool = False) -> list:
    """Load meetings with optional filters.
    Args:
        org: Filter by organization name (case-insensitive)
        offering: Filter by offering name
        status: Single status string or list of statuses to include
        future_only: Only meetings with meeting_date >= today
        past_only: Only meetings with meeting_date < today
    Returns list of meeting dicts, sorted by meeting_date (asc for future, desc for past).
    """
    meetings = _load_meetings_raw()
    today = date.today().isoformat()

    # Auto-transition: mark past 'scheduled' meetings as 'completed'
    changed = False
    for m in meetings:
        if m.get('status') == 'scheduled' and m.get('meeting_date', '') < today:
            if not m.get('notes_raw'):
                m['status'] = 'completed'
                m['updated_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                changed = True
    if changed:
        _save_meetings_raw(meetings)

    if org:
        meetings = [m for m in meetings if m.get('org', '').lower() == org.lower()]
    if offering:
        meetings = [m for m in meetings if m.get('offering', '').lower() == offering.lower()]
    if status:
        statuses = [status] if isinstance(status, str) else status
        meetings = [m for m in meetings if m.get('status') in statuses]
    if future_only:
        meetings = [m for m in meetings if m.get('meeting_date', '') >= today]
    if past_only:
        meetings = [m for m in meetings if m.get('meeting_date', '') < today]

    # Sort: future meetings ascending, past meetings descending
    if future_only:
        meetings.sort(key=lambda m: m.get('meeting_date', ''))
    else:
        meetings.sort(key=lambda m: m.get('meeting_date', ''), reverse=True)

    return meetings


def get_meeting(meeting_id: str) -> dict | None:
    """Get a single meeting by UUID."""
    for m in _load_meetings_raw():
        if m.get('id') == meeting_id:
            return m
    return None


def save_meeting(org: str, offering: str, meeting_date: str,
                 meeting_time: str = '', title: str = '',
                 attendees: str = '', source: str = 'manual',
                 graph_event_id: str = None, notes_raw: str = None,
                 created_by: str = 'oscar') -> dict:
    """Create a new meeting record. Enforces graph_event_id uniqueness
    and fuzzy dedup (same org + date ±24h).
    Returns the new or matched meeting dict."""
    meetings = _load_meetings_raw()
    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    # Tier 1 dedup: graph_event_id exact match
    if graph_event_id:
        for m in meetings:
            if m.get('graph_event_id') == graph_event_id:
                return m  # Already exists

    # Tier 2 dedup: same org + date within ±24h (only for notes without event ID)
    if not graph_event_id and notes_raw:
        match = _find_meeting_by_fuzzy(meetings, org, meeting_date)
        if match:
            # Attach notes to existing meeting
            if notes_raw and not match.get('notes_raw'):
                match['notes_raw'] = notes_raw
                match['updated_at'] = now
                if match.get('status') == 'scheduled':
                    match['status'] = 'completed'
                _save_meetings_raw(meetings)
            return match

    entry = {
        'id': str(uuid.uuid4()),
        'org': org,
        'offering': offering,
        'meeting_date': meeting_date.strip(),
        'meeting_time': (meeting_time or '').strip(),
        'title': (title or '').strip(),
        'attendees': (attendees or '').strip(),
        'graph_event_id': graph_event_id,
        'source': source if source in MEETING_SOURCES else 'manual',
        'status': 'scheduled',
        'notes_raw': notes_raw,
        'notes_summary': None,
        'transcript_url': None,
        'insights': [],
        'created_by': created_by,
        'created_at': now,
        'updated_at': now,
    }

    # If notes provided, auto-set to completed
    if notes_raw:
        entry['status'] = 'completed'

    meetings.append(entry)
    _save_meetings_raw(meetings)
    return entry


def update_meeting(meeting_id: str, **fields) -> dict | None:
    """Update fields on a meeting. Returns updated meeting or None."""
    meetings = _load_meetings_raw()
    for m in meetings:
        if m.get('id') == meeting_id:
            for key, val in fields.items():
                if key != 'id':  # never overwrite id
                    m[key] = val
            m['updated_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            _save_meetings_raw(meetings)
            return m
    return None


def delete_meeting(meeting_id: str) -> bool:
    """Delete a meeting by UUID. Returns True if found and removed."""
    meetings = _load_meetings_raw()
    new_meetings = [m for m in meetings if m.get('id') != meeting_id]
    if len(new_meetings) == len(meetings):
        return False
    _save_meetings_raw(new_meetings)
    return True


def _find_meeting_by_fuzzy(meetings: list, org: str, meeting_date: str) -> dict | None:
    """Fuzzy match: find an existing meeting for the same org
    with a date within ±1 day."""
    try:
        target = datetime.strptime(meeting_date, '%Y-%m-%d')
    except ValueError:
        return None

    for m in meetings:
        if m.get('org', '').lower() != org.lower():
            continue
        try:
            m_date = datetime.strptime(m.get('meeting_date', ''), '%Y-%m-%d')
        except ValueError:
            continue
        if abs((m_date - target).days) <= 1:
            return m
    return None


def approve_meeting_insight(meeting_id: str, insight_id: str,
                            username: str = 'oscar') -> dict | None:
    """Approve a meeting insight. Writes to prospect Notes field.
    Returns updated meeting or None."""
    meetings = _load_meetings_raw()
    for m in meetings:
        if m.get('id') != meeting_id:
            continue
        for insight in m.get('insights', []):
            if insight.get('id') != insight_id:
                continue
            insight['status'] = 'approved'
            insight['reviewed_by'] = username
            insight['reviewed_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

            # Write approved insight to prospect Notes
            prefix = f"[Meeting {m.get('meeting_date', '')}] "
            notes_text = prefix + insight['text']
            org = m.get('org', '')
            offering = m.get('offering', '')
            if org and offering:
                prospect = get_prospect(org, offering)
                if prospect:
                    existing_notes = prospect.get('Notes', '')
                    new_notes = (existing_notes + '\n' + notes_text).strip() if existing_notes else notes_text
                    update_prospect_field(org, offering, 'notes', new_notes)

            # Check if all insights are reviewed
            _check_meeting_reviewed(m)
            m['updated_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            _save_meetings_raw(meetings)
            return m
    return None


def dismiss_meeting_insight(meeting_id: str, insight_id: str,
                            username: str = 'oscar') -> dict | None:
    """Dismiss a meeting insight (does NOT write to prospect).
    Returns updated meeting or None."""
    meetings = _load_meetings_raw()
    for m in meetings:
        if m.get('id') != meeting_id:
            continue
        for insight in m.get('insights', []):
            if insight.get('id') != insight_id:
                continue
            insight['status'] = 'dismissed'
            insight['reviewed_by'] = username
            insight['reviewed_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            _check_meeting_reviewed(m)
            m['updated_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            _save_meetings_raw(meetings)
            return m
    return None


def _check_meeting_reviewed(meeting: dict) -> None:
    """If all insights are approved or dismissed, set status to 'reviewed'."""
    insights = meeting.get('insights', [])
    if not insights:
        return
    if all(i.get('status') in ('approved', 'dismissed') for i in insights):
        meeting['status'] = 'reviewed'


def process_meeting_notes(meeting_id: str) -> dict | None:
    """Run AI processing on meeting notes. Generates summary + insights.
    Returns updated meeting or None.

    Uses Claude API (same pattern as brief_synthesizer.py).
    """
    meeting = get_meeting(meeting_id)
    if not meeting or not meeting.get('notes_raw'):
        return None

    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic()
    prompt = f"""Meeting: {meeting.get('title', 'Untitled')} with {meeting.get('org', '')} on {meeting.get('meeting_date', '')}
Attendees: {meeting.get('attendees', 'Unknown')}

NOTES:
{meeting['notes_raw']}

Return JSON only:
{{
  "summary": "2-3 paragraph narrative summary of the meeting",
  "insights": [
    "Specific actionable insight about this investor's interest, concerns, or next steps",
    ...
  ]
}}
Insights should be specific, concise (1-2 sentences each), and relevant to fundraising
relationship management. Do not include generic observations. Max 5 insights."""

    try:
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1000,
            system="You are an analyst extracting intelligence from meeting notes for a real estate private equity fundraising CRM.",
            messages=[{'role': 'user', 'content': prompt}],
        )
        content = response.content[0].text.strip()

        # Parse JSON from response (handle markdown code blocks)
        if '```' in content:
            content = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
            content = content.group(1) if content else '{}'
        result = json.loads(content)
    except Exception:
        # Fallback: no AI processing
        result = {'summary': meeting['notes_raw'][:500], 'insights': []}

    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    insights = []
    for text in result.get('insights', []):
        insights.append({
            'id': str(uuid.uuid4()),
            'text': str(text),
            'status': 'pending',
            'reviewed_by': None,
            'reviewed_at': None,
            'created_at': now,
        })

    meetings = _load_meetings_raw()
    for m in meetings:
        if m.get('id') == meeting_id:
            m['notes_summary'] = result.get('summary', '')
            m['insights'] = insights
            if m.get('status') == 'scheduled':
                m['status'] = 'completed'
            m['updated_at'] = now

            # Write interaction log breadcrumb
            append_interaction({
                'date': m.get('meeting_date', date.today().isoformat()),
                'org': m.get('org', ''),
                'type': 'Meeting',
                'offering': m.get('offering', ''),
                'Subject': m.get('title') or 'Meeting',
                'Summary': f"Meeting with {m.get('attendees', '')} — {(m.get('notes_summary') or 'Notes pending')[:100]}",
                'Source': 'meeting',
            })
            break

    _save_meetings_raw(meetings)
    return get_meeting(meeting_id)
