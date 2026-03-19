"""
CRM data reader/writer for all markdown files in crm/ and memory/people/.
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
MEMORY_ROOT = os.path.join(PROJECT_ROOT, "memory")
PEOPLE_ROOT = os.path.join(PROJECT_ROOT, "contacts")
TASKS_MD_PATH = os.path.join(PROJECT_ROOT, "TASKS.md")
BRIEFS_PATH = os.path.join(CRM_ROOT, "briefs.json")
PROSPECT_NOTES_PATH = os.path.join(CRM_ROOT, "prospect_notes.json")
PROSPECT_MEETINGS_PATH = os.path.join(CRM_ROOT, "prospect_meetings.json")
MEETINGS_PATH = os.path.join(CRM_ROOT, "meetings.json")
ORG_NOTES_PATH = os.path.join(CRM_ROOT, "org_notes.json")

# Field write order for prospects
PROSPECT_FIELD_ORDER = [
    "Stage", "Target",
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
    'notes', 'closing'
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


def get_org_by_alias(alias: str) -> str | None:
    """Look up org canonical name by alias (case-insensitive exact match).
    Returns the canonical org name, or None if no match found."""
    if not alias:
        return None
    alias_lower = alias.strip().lower()
    for org in load_organizations():
        aliases_raw = org.get('Aliases', '')
        if aliases_raw:
            # Parse comma-separated aliases
            aliases = [a.strip() for a in aliases_raw.split(',') if a.strip()]
            for a in aliases:
                if a.lower() == alias_lower:
                    return org['name']
    return None


def get_org_aliases_map() -> dict:
    """Build {alias_lower: org_name} for all orgs with aliases.
    Used for bulk lookups. If multiple orgs share an alias, first wins."""
    alias_map = {}
    for org in load_organizations():
        aliases_raw = org.get('Aliases', '')
        if aliases_raw:
            aliases = [a.strip() for a in aliases_raw.split(',') if a.strip()]
            for a in aliases:
                key = a.lower()
                if key not in alias_map:
                    alias_map[key] = org['name']
    return alias_map


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
    """Parse a memory/people/<slug>.md file into a dict."""
    path = os.path.join(PEOPLE_ROOT, f"{slug}.md")
    if not os.path.exists(path):
        return None
    text = _read_file(path)
    lines = text.splitlines()
    person = {'slug': slug, 'name': '', 'organization': '', 'role': '',
              'email': '', 'phone': '', 'type': '', 'is_primary': False}
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
                elif key == 'primary':
                    person['is_primary'] = val.lower() == 'true'
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
                elif key == 'primary':
                    person['is_primary'] = val.lower() == 'true'
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


def _set_contact_primary_field(slug: str, value: bool) -> None:
    """Write or remove the Primary field in a contact file."""
    path = os.path.join(PEOPLE_ROOT, f"{slug}.md")
    if not os.path.exists(path):
        return
    text = _read_file(path)
    lines = text.splitlines()
    primary_re = re.compile(r'^\s*-?\s*\*\*Primary:\*\*\s*.*', re.IGNORECASE)
    existing_idx = next((i for i, line in enumerate(lines) if primary_re.match(line)), None)

    if not value:
        if existing_idx is not None:
            lines.pop(existing_idx)
            _write_file(path, '\n'.join(lines) + '\n')
        return

    if existing_idx is not None:
        lines[existing_idx] = '- **Primary:** true'
    else:
        # Insert after the Organization line, or after H1 if not found
        insert_idx = 1
        for i, line in enumerate(lines):
            if re.match(r'\s*-?\s*\*\*Organization:\*\*', line, re.IGNORECASE):
                insert_idx = i + 1
                break
        lines.insert(insert_idx, '- **Primary:** true')
    _write_file(path, '\n'.join(lines) + '\n')


def get_primary_contact(org: str) -> dict | None:
    """Return the contact dict with is_primary=True for this org, or None."""
    for contact in get_contacts_for_org(org):
        if contact.get('is_primary'):
            return contact
    return None


def set_primary_contact(org: str, contact_name: str) -> bool:
    """Mark contact_name as primary for org, clearing any existing primary first.
    Returns True on success, False if contact not found."""
    contacts = get_contacts_for_org(org)
    target_slug = None
    for c in contacts:
        if c.get('name', '').lower() == contact_name.lower():
            target_slug = c.get('slug')
        else:
            if c.get('is_primary'):
                _set_contact_primary_field(c['slug'], False)
    if target_slug is None:
        return False
    _set_contact_primary_field(target_slug, True)
    return True


def clear_primary_contact(org: str) -> None:
    """Remove Primary: true from all contacts for this org."""
    for c in get_contacts_for_org(org):
        if c.get('is_primary'):
            _set_contact_primary_field(c['slug'], False)


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
    """Create memory/people/<slug>.md and update contacts_index.md. Returns slug."""
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
    """Load all person files from memory/people/. Returns list of person dicts sorted by name."""
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
    primary = get_primary_contact(org)
    prospect['Primary Contact'] = primary['name'] if primary else ''
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


def stamp_last_scan() -> None:
    """Stamp lastScan to now in email_log.json.

    Call this at the end of every email scan pass — regardless of whether any
    emails matched. This advances the scan window so the next run does not
    re-process the same emails.

    This is intentionally separate from add_emails_to_log() so that the scan
    window always advances even when no emails are logged (e.g. quiet day, all
    deduped). It is also a safeguard: if add_emails_to_log() is skipped, this
    call alone is sufficient to prevent the stuck-lastScan bug.
    """
    log = load_email_log()
    log['lastScan'] = datetime.now().isoformat() + 'Z'
    save_email_log(log)


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
# Meetings (full CRUD, backed by crm/meetings.json)
# ---------------------------------------------------------------------------

def _save_meetings_raw(meetings: list) -> None:
    """Write the full meetings list to MEETINGS_PATH."""
    os.makedirs(os.path.dirname(MEETINGS_PATH), exist_ok=True)
    with open(MEETINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(meetings, f, indent=2, ensure_ascii=False)


def _load_meetings_raw() -> list[dict]:
    """Load raw meetings list without any filters or transformations."""
    if not os.path.exists(MEETINGS_PATH):
        return []

    try:
        with open(MEETINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _find_meeting_by_fuzzy(org: str, meeting_date: str) -> dict | None:
    """Find existing meeting by org + date proximity (±1 day). Tier 2 dedup."""
    meetings = _load_meetings_raw()
    try:
        target_date = date.fromisoformat(meeting_date)
    except (ValueError, TypeError):
        return None
    for m in meetings:
        if m.get('org', '').lower() != org.lower():
            continue
        try:
            m_date = date.fromisoformat(m['meeting_date'])
        except (ValueError, TypeError):
            continue
        if abs((m_date - target_date).days) <= 1:
            return m
    return None


def load_meetings(org=None, offering=None, status=None, future_only=False, past_only=False) -> list[dict]:
    """Load meetings with optional filters.
    
    Args:
        org: Filter by organization name
        offering: Filter by offering name
        status: Single status string or list of statuses (e.g. 'scheduled', ['completed', 'reviewed'])
        future_only: Only return meetings with meeting_date >= today
        past_only: Only return meetings with meeting_date < today
    
    Returns:
        List of meeting dicts sorted by meeting_date descending (newest first)
    """
    if not os.path.exists(MEETINGS_PATH):
        return []
    
    try:
        with open(MEETINGS_PATH, 'r', encoding='utf-8') as f:
            meetings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    # Auto-transition past scheduled meetings to completed
    today = date.today()
    changed = False
    for m in meetings:
        if m.get('status') == 'scheduled':
            try:
                meeting_date = date.fromisoformat(m['meeting_date'])
                if meeting_date < today:
                    m['status'] = 'completed'
                    m['updated_at'] = datetime.utcnow().isoformat() + 'Z'
                    changed = True
            except (ValueError, TypeError):
                pass
    if changed:
        _save_meetings_raw(meetings)

    # Deduplicate: keep first meeting per org+date (first = has more data or earlier created)
    seen = {}
    deduped = []
    for m in meetings:
        key = (m.get('org', '').lower().strip(), m.get('meeting_date', ''))
        if key[0] and key in seen:
            # Merge useful fields from duplicate into the keeper
            keeper = seen[key]
            if m.get('graph_event_id') and not keeper.get('graph_event_id'):
                keeper['graph_event_id'] = m['graph_event_id']
            if m.get('notes_raw') and not keeper.get('notes_raw'):
                keeper['notes_raw'] = m['notes_raw']
            if m.get('notes_summary') and not keeper.get('notes_summary'):
                keeper['notes_summary'] = m['notes_summary']
            continue
        seen[key] = m
        deduped.append(m)

    if len(deduped) < len(meetings):
        _save_meetings_raw(deduped)
        meetings = deduped

    # Apply filters
    results = meetings
    
    if org:
        results = [m for m in results if m.get('org', '').lower() == org.lower()]
    
    if offering:
        results = [m for m in results if m.get('offering', '').lower() == offering.lower()]
    
    if status:
        if isinstance(status, str):
            status = [status]
        results = [m for m in results if m.get('status') in status]
    
    today = date.today().isoformat()
    
    if future_only:
        results = [m for m in results if m.get('meeting_date', '') >= today]
    
    if past_only:
        results = [m for m in results if m.get('meeting_date', '') < today]
    
    # Sort by meeting_date descending
    results.sort(key=lambda m: m.get('meeting_date', ''), reverse=True)
    
    return results


def get_meeting(meeting_id: str) -> dict | None:
    """Get a single meeting by UUID."""
    if not os.path.exists(MEETINGS_PATH):
        return None
    
    try:
        with open(MEETINGS_PATH, 'r', encoding='utf-8') as f:
            meetings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    
    for meeting in meetings:
        if meeting.get('id') == meeting_id:
            return meeting
    
    return None


def save_meeting(org: str, offering: str, meeting_date: str, title: str = '', 
                 attendees: str = '', source: str = 'manual', graph_event_id: str = None,
                 meeting_time: str = '', notes_raw: str = '', transcript_url: str = '',
                 created_by: str = 'oscar') -> dict:
    """Create a new meeting with two-tier deduplication.
    
    Dedup logic:
        1. Exact graph_event_id match (if provided) → return existing
        2. Fuzzy match: same org AND meeting_date ±1 day (any status) → return existing
    
    Args:
        org: Organization name
        offering: Offering name
        meeting_date: ISO date string (YYYY-MM-DD)
        title: Meeting title
        attendees: Comma-separated attendees
        source: 'manual' or 'graph'
        graph_event_id: Calendar event ID from Graph API
        meeting_time: Time string (optional)
        notes_raw: Raw meeting notes
        transcript_url: URL to meeting transcript
        created_by: Username who created the meeting
    
    Returns:
        The created or existing meeting dict
    """
    meetings = []
    if os.path.exists(MEETINGS_PATH):
        try:
            with open(MEETINGS_PATH, 'r', encoding='utf-8') as f:
                meetings = json.load(f)
        except (json.JSONDecodeError, OSError):
            meetings = []
    
    # Dedup tier 1: exact graph_event_id match
    if graph_event_id:
        for meeting in meetings:
            if meeting.get('graph_event_id') == graph_event_id:
                return meeting
    
    # Dedup tier 2: fuzzy org+date±1 day match (any status)
    try:
        target_date = datetime.strptime(meeting_date, '%Y-%m-%d').date()
        org_lower = org.lower().strip()

        for meeting in meetings:
            if meeting.get('org', '').lower().strip() != org_lower:
                continue

            meeting_date_str = meeting.get('meeting_date', '')
            if not meeting_date_str:
                continue

            try:
                existing_date = datetime.strptime(meeting_date_str, '%Y-%m-%d').date()
                delta = abs((existing_date - target_date).days)
                if delta <= 1:
                    # Found fuzzy match — merge new data into existing
                    if notes_raw and not meeting.get('notes_raw'):
                        meeting['notes_raw'] = notes_raw
                    if meeting.get('status') == 'scheduled' and notes_raw:
                        meeting['status'] = 'completed'
                    if title and not meeting.get('title'):
                        meeting['title'] = title
                    if attendees and not meeting.get('attendees'):
                        meeting['attendees'] = attendees
                    if transcript_url and not meeting.get('transcript_url'):
                        meeting['transcript_url'] = transcript_url
                    if graph_event_id and not meeting.get('graph_event_id'):
                        meeting['graph_event_id'] = graph_event_id
                    meeting['updated_at'] = datetime.utcnow().isoformat() + 'Z'
                    _save_meetings_raw(meetings)
                    return meeting
            except ValueError:
                continue
    except ValueError:
        pass
    
    # No match — create new meeting
    now = datetime.utcnow().isoformat() + 'Z'
    meeting = {
        'id': str(uuid.uuid4()),
        'org': org,
        'offering': offering,
        'meeting_date': meeting_date,
        'meeting_time': meeting_time,
        'title': title,
        'attendees': attendees,
        'graph_event_id': graph_event_id,
        'source': source,
        'status': 'completed' if notes_raw else 'scheduled',
        'notes_raw': notes_raw,
        'notes_summary': None,
        'transcript_url': transcript_url,
        'insights': [],
        'created_by': created_by,
        'created_at': now,
        'updated_at': now,
    }
    
    meetings.append(meeting)
    
    os.makedirs(os.path.dirname(MEETINGS_PATH), exist_ok=True)
    with open(MEETINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(meetings, f, indent=2, ensure_ascii=False)
    
    return meeting


def update_meeting(meeting_id: str, **fields) -> dict | None:
    """Update arbitrary fields on a meeting.
    
    Args:
        meeting_id: Meeting UUID
        **fields: Any meeting fields to update
    
    Returns:
        Updated meeting dict or None if not found
    """
    if not os.path.exists(MEETINGS_PATH):
        return None
    
    try:
        with open(MEETINGS_PATH, 'r', encoding='utf-8') as f:
            meetings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    
    for meeting in meetings:
        if meeting.get('id') == meeting_id:
            # Update fields
            for key, value in fields.items():
                if key not in ('id', 'created_by', 'created_at'):
                    meeting[key] = value
            
            meeting['updated_at'] = datetime.utcnow().isoformat() + 'Z'
            
            # Auto-transition status to 'completed' if notes_raw is added
            if 'notes_raw' in fields and fields['notes_raw'] and meeting.get('status') == 'scheduled':
                meeting['status'] = 'completed'
            
            # Write back
            with open(MEETINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(meetings, f, indent=2, ensure_ascii=False)
            
            return meeting
    
    return None


def delete_meeting(meeting_id: str) -> bool:
    """Delete a meeting by UUID.
    
    Returns:
        True if meeting was found and deleted, False otherwise
    """
    if not os.path.exists(MEETINGS_PATH):
        return False
    
    try:
        with open(MEETINGS_PATH, 'r', encoding='utf-8') as f:
            meetings = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    
    original_len = len(meetings)
    meetings = [m for m in meetings if m.get('id') != meeting_id]
    
    if len(meetings) == original_len:
        return False
    
    with open(MEETINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(meetings, f, indent=2, ensure_ascii=False)
    
    return True


def process_meeting_notes(meeting_id: str) -> dict | None:
    """Process meeting notes with Claude API.
    
    Generates:
        - notes_summary: Concise summary of meeting notes
        - insights: List of structured action items and key decisions
    
    Each insight has:
        - id: UUID
        - type: 'action_item', 'decision', 'follow_up'
        - text: The insight text
        - status: 'pending' (awaiting review)
    
    Returns:
        Updated meeting dict or None if not found
    """
    meeting = get_meeting(meeting_id)
    if not meeting:
        return None
    
    notes_raw = meeting.get('notes_raw', '').strip()
    if not notes_raw:
        return meeting
    
    # Call Claude API
    import anthropic
    
    client = anthropic.Anthropic()
    
    system_prompt = """You are a meeting intelligence assistant. Extract key information from meeting notes.

Return a JSON object with:
{
  "summary": "2-3 sentence summary of the meeting",
  "insights": [
    {"type": "action_item", "text": "specific action item with owner if mentioned"},
    {"type": "decision", "text": "key decision made"},
    {"type": "follow_up", "text": "follow-up needed"}
  ]
}

Only include insights that are clear and actionable. If no insights, return empty array."""
    
    user_prompt = f"""Meeting: {meeting.get('title', 'Untitled')}
Date: {meeting.get('meeting_date', '')}
Attendees: {meeting.get('attendees', '')}

Notes:
{notes_raw}"""
    
    try:
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1500,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_prompt}]
        )
        
        content = response.content[0].text
        
        # Parse JSON
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        result = json.loads(content)
        
        summary = result.get('summary', '')
        insights_raw = result.get('insights', [])
        
        # Add IDs and status to insights
        insights = []
        for insight in insights_raw:
            insights.append({
                'id': str(uuid.uuid4()),
                'type': insight.get('type', 'action_item'),
                'text': insight.get('text', ''),
                'status': 'pending',
            })
        
        # Update meeting
        return update_meeting(meeting_id, notes_summary=summary, insights=insights)
        
    except Exception as e:
        # Processing failed - meeting is still saved, just not processed
        print(f"Failed to process meeting notes: {e}")
        return meeting


def approve_meeting_insight(meeting_id: str, insight_id: str, username: str) -> dict | None:
    """Approve a meeting insight — writes to prospect Notes field.

    Args:
        meeting_id: Meeting UUID
        insight_id: Insight UUID
        username: User approving the insight

    Returns:
        Updated meeting dict or None if not found
    """
    meeting = get_meeting(meeting_id)
    if not meeting:
        return None

    insights = meeting.get('insights', [])
    insight = None

    for ins in insights:
        if ins.get('id') == insight_id:
            insight = ins
            break

    if not insight:
        return None

    # Mark as approved
    insight['status'] = 'approved'
    insight['reviewed_by'] = username
    insight['reviewed_at'] = datetime.utcnow().isoformat() + 'Z'

    # Write to prospect Notes field
    org = meeting.get('org', '')
    offering = meeting.get('offering', '')
    meeting_date = meeting.get('meeting_date', '')

    if org and offering:
        prospect = get_prospect(org, offering)
        if prospect:
            existing_notes = prospect.get('Notes', '').strip()
            insight_text = insight.get('text', '').strip()
            note_with_date = f"[Meeting {meeting_date}] {insight_text}"

            if existing_notes:
                new_notes = f"{existing_notes} | {note_with_date}"
            else:
                new_notes = note_with_date

            update_prospect_field(org, offering, 'notes', new_notes)

    # Check if all insights are reviewed
    all_reviewed = all(ins.get('status') in ('approved', 'dismissed') for ins in insights)
    if all_reviewed:
        meeting['status'] = 'reviewed'

    # Update meeting with new insights and potentially new status
    meeting['insights'] = insights
    meeting['updated_at'] = datetime.utcnow().isoformat() + 'Z'

    # Write back to meetings.json
    meetings = _load_meetings_raw()
    for i, m in enumerate(meetings):
        if m.get('id') == meeting_id:
            meetings[i] = meeting
            break
    _save_meetings_raw(meetings)

    return meeting


def dismiss_meeting_insight(meeting_id: str, insight_id: str, username: str) -> dict | None:
    """Dismiss a meeting insight — does NOT write to prospect Notes.

    Args:
        meeting_id: Meeting UUID
        insight_id: Insight UUID
        username: User dismissing the insight

    Returns:
        Updated meeting dict or None if not found
    """
    meeting = get_meeting(meeting_id)
    if not meeting:
        return None

    insights = meeting.get('insights', [])

    for ins in insights:
        if ins.get('id') == insight_id:
            ins['status'] = 'dismissed'
            ins['reviewed_by'] = username
            ins['reviewed_at'] = datetime.utcnow().isoformat() + 'Z'
            break

    # Check if all insights are reviewed
    all_reviewed = all(ins.get('status') in ('approved', 'dismissed') for ins in insights)
    if all_reviewed:
        meeting['status'] = 'reviewed'

    # Update meeting with new insights and potentially new status
    meeting['insights'] = insights
    meeting['updated_at'] = datetime.utcnow().isoformat() + 'Z'

    # Write back to meetings.json
    meetings = _load_meetings_raw()
    for i, m in enumerate(meetings):
        if m.get('id') == meeting_id:
            meetings[i] = meeting
            break
    _save_meetings_raw(meetings)

    return meeting


# ---------------------------------------------------------------------------
# Org Notes (backed by crm/org_notes.json)
# ---------------------------------------------------------------------------

def load_org_notes(org: str) -> list[dict]:
    """Load notes for an organization.
    
    Returns:
        List of note dicts sorted by date descending (newest first)
    """
    if not os.path.exists(ORG_NOTES_PATH):
        return []
    
    try:
        with open(ORG_NOTES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    
    notes = data.get(org, [])
    notes.sort(key=lambda n: n.get('date', ''), reverse=True)
    return notes


def save_org_note(org: str, author: str, text: str) -> dict:
    """Save a note for an organization.
    
    Args:
        org: Organization name
        author: Note author username
        text: Note text
    
    Returns:
        The created note dict
    """
    data = {}
    if os.path.exists(ORG_NOTES_PATH):
        try:
            with open(ORG_NOTES_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    
    note = {
        'date': date.today().isoformat(),
        'author': author,
        'text': text.strip(),
    }
    
    data.setdefault(org, []).append(note)
    
    os.makedirs(os.path.dirname(ORG_NOTES_PATH), exist_ok=True)
    with open(ORG_NOTES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return note


# ---------------------------------------------------------------------------
# Task Grouping (wrappers over get_all_prospect_tasks)
# ---------------------------------------------------------------------------

def get_tasks_grouped_by_prospect() -> list[dict]:
    """Group tasks by prospect organization.

    Returns:
        List of dicts: [{'org': str, 'tasks': [task, ...], 'target': int}, ...]
        Sorted by prospect target descending
    """
    all_tasks = get_all_prospect_tasks()

    # Load prospect data and build org -> target map
    prospects = load_prospects()
    org_targets = {}
    for prospect in prospects:
        org = prospect.get('org', '')
        target = _parse_currency(prospect.get('Target', '0'))
        org_targets[org] = target

    # Priority normalization map
    priority_map = {
        'high': 'Hi', 'hi': 'Hi',
        'normal': 'Med', 'med': 'Med', 'medium': 'Med',
        'low': 'Lo', 'lo': 'Lo'
    }

    # Group by org, filtering and normalizing
    groups = {}
    for task in all_tasks:
        # Filter out done tasks
        if task.get('status') == 'done':
            continue

        # Filter out tasks without owner
        owner = task.get('owner', '').strip()
        if not owner:
            continue

        org = task.get('org', '')
        if not org:
            continue

        # Normalize priority
        raw_priority = task.get('priority', '').lower()
        task['priority'] = priority_map.get(raw_priority, task.get('priority', 'Med'))

        groups.setdefault(org, []).append(task)

    # Convert to list format with target
    result = []
    for org, tasks in groups.items():
        target = org_targets.get(org, 0)
        result.append({'org': org, 'tasks': tasks, 'target': target})

    # Sort by target descending
    result.sort(key=lambda x: x['target'], reverse=True)

    return result


def get_tasks_grouped_by_owner() -> list[dict]:
    """Group tasks by owner.

    Returns:
        List of dicts: [{'owner': str, 'tasks': [task, ...], 'max_target': int}, ...]
        Sorted by max_target descending
    """
    all_tasks = get_all_prospect_tasks()

    # Load prospect data and build org -> target map
    prospects = load_prospects()
    org_targets = {}
    for prospect in prospects:
        org = prospect.get('org', '')
        target = _parse_currency(prospect.get('Target', '0'))
        org_targets[org] = target

    # Priority order for sorting
    priority_order = {'Hi': 0, 'Med': 1, 'Lo': 2}

    # Group by owner, filtering done tasks
    groups = {}
    for task in all_tasks:
        # Filter out done tasks
        if task.get('status') == 'done':
            continue

        owner = task.get('owner', '').strip()
        if not owner:
            continue

        groups.setdefault(owner, []).append(task)

    # Convert to list format with max_target
    result = []
    for owner, tasks in groups.items():
        # Calculate max_target for this owner
        max_target = 0
        for task in tasks:
            org = task.get('org', '')
            target = org_targets.get(org, 0)
            if target > max_target:
                max_target = target

        # Sort tasks by priority (Hi, Med, Lo)
        tasks.sort(key=lambda t: priority_order.get(t.get('priority', 'Med'), 1))

        result.append({'owner': owner, 'tasks': tasks, 'max_target': max_target})

    # Sort by max_target descending
    result.sort(key=lambda x: x['max_target'], reverse=True)

    return result


# ---------------------------------------------------------------------------
# Organization Merge
# ---------------------------------------------------------------------------

def get_merge_preview(source: str, target: str) -> dict:
    """Preview what will be merged when merging source org into target org.

    Returns counts of data that will be migrated.
    """
    # Count prospects
    source_prospects = get_prospects_for_org(source)

    # Count contacts
    source_contacts = get_contacts_for_org(source)

    # Count email log entries
    email_log = load_email_log()
    email_count = sum(
        1 for e in email_log.get('emails', [])
        if e.get('orgMatch', '').lower() == source.lower()
    )

    # Count briefs
    briefs_data = _load_briefs()
    brief_count = sum(
        1 for key in briefs_data.get('prospect', {}).keys()
        if key.split('::')[0].lower() == source.lower()
    )

    # Count prospect notes
    notes_data = {}
    if os.path.exists(PROSPECT_NOTES_PATH):
        with open(PROSPECT_NOTES_PATH, 'r', encoding='utf-8') as f:
            notes_data = json.load(f)
    notes_count = sum(
        len(entries) for key, entries in notes_data.items()
        if key.split('::')[0].lower() == source.lower()
    )

    # Count prospect meetings
    meetings_data = {}
    if os.path.exists(PROSPECT_MEETINGS_PATH):
        with open(PROSPECT_MEETINGS_PATH, 'r', encoding='utf-8') as f:
            meetings_data = json.load(f)
    meetings_count = sum(
        len(entries) for key, entries in meetings_data.items()
        if key.split('::')[0].lower() == source.lower()
    )

    return {
        'source': source,
        'target': target,
        'prospects': len(source_prospects),
        'contacts': len(source_contacts),
        'emails': email_count,
        'briefs': brief_count,
        'notes': notes_count,
        'meetings': meetings_count,
    }


def merge_organizations(source: str, target: str) -> dict:
    """Merge source org into target org, then delete source.

    This is a destructive operation. All data from source is migrated to target:
    - Org fields are combined (aliases union, notes concatenated, etc.)
    - Prospects are re-parented
    - Contacts are moved
    - People files Company field updated
    - Email log entries re-attributed
    - Briefs re-keyed
    - Prospect notes and meetings re-keyed
    - Source org name added as alias on target
    - Source org deleted

    Returns dict with migration stats.
    """
    # Validate both orgs exist
    source_org = get_organization(source)
    target_org = get_organization(target)

    if not source_org:
        raise ValueError(f"Source org '{source}' not found")
    if not target_org:
        raise ValueError(f"Target org '{target}' not found")

    stats = {
        'prospects_moved': 0,
        'contacts_moved': 0,
        'people_updated': 0,
        'emails_updated': 0,
        'briefs_rekeyed': 0,
        'notes_rekeyed': 0,
        'meetings_rekeyed': 0,
    }

    # 1. Combine org fields
    _merge_org_fields(source, target, source_org, target_org)

    # 2. Re-parent prospects
    stats['prospects_moved'] = _merge_prospects(source, target)

    # 3. Move contacts
    stats['contacts_moved'] = _merge_contacts(source, target)

    # 4. Update people files
    stats['people_updated'] = _merge_people_files(source, target)

    # 5. Update email log
    stats['emails_updated'] = _merge_email_log(source, target)

    # 6. Re-key briefs
    stats['briefs_rekeyed'] = _merge_briefs(source, target)

    # 7. Re-key prospect notes
    stats['notes_rekeyed'] = _merge_prospect_notes(source, target)

    # 8. Re-key prospect meetings
    stats['meetings_rekeyed'] = _merge_prospect_meetings(source, target)

    # 9. Delete source org
    delete_organization(source)

    return {'ok': True, **stats}


def _merge_org_fields(source: str, target: str, source_org: dict, target_org: dict) -> None:
    """Combine org fields per the merge strategy and add source name as alias."""
    merged = dict(target_org)

    # Type: keep target's, fall back to source's
    if not merged.get('Type') and source_org.get('Type'):
        merged['Type'] = source_org['Type']

    # Domain: keep target's (single-valued field)
    # If target has no domain, use source's
    if not merged.get('Domain') and source_org.get('Domain'):
        merged['Domain'] = source_org['Domain']

    # Aliases: union of both lists + add source org name
    target_aliases = set()
    if merged.get('Aliases'):
        target_aliases = {a.strip() for a in merged['Aliases'].split(',') if a.strip()}
    if source_org.get('Aliases'):
        source_aliases = {a.strip() for a in source_org['Aliases'].split(',') if a.strip()}
        target_aliases.update(source_aliases)
    # Add source org canonical name as an alias
    target_aliases.add(source)
    merged['Aliases'] = ', '.join(sorted(target_aliases))

    # Notes: concatenate (target first, then separator, then source)
    target_notes = (merged.get('Notes') or '').strip()
    source_notes = (source_org.get('Notes') or '').strip()
    if target_notes and source_notes:
        # Avoid duplicating identical notes
        if target_notes != source_notes:
            merged['Notes'] = f"{target_notes}\n\n---\n\n{source_notes}"
    elif source_notes:
        merged['Notes'] = source_notes

    # Write combined org
    write_organization(target, merged)


def _merge_prospects(source: str, target: str) -> int:
    """Re-parent all prospects from source to target in prospects.md.

    Returns count of prospects moved.
    """
    path = os.path.join(CRM_ROOT, "prospects.md")
    if not os.path.exists(path):
        return 0

    text = _read_file(path)
    lines = text.splitlines()
    out = []
    count = 0

    for line in lines:
        # Check for prospect heading: ### OrgName
        h3 = re.match(r'^### (.+)', line)
        if h3 and h3.group(1).strip().lower() == source.lower():
            # Replace source org name with target org name
            out.append(f"### {target}")
            count += 1
        else:
            out.append(line)

    if count > 0:
        _write_file(path, '\n'.join(out))

    return count


def _merge_contacts(source: str, target: str) -> int:
    """Move all contacts from source org to target org in contacts_index.md.

    Returns count of contacts moved.
    """
    index_path = os.path.join(CRM_ROOT, "contacts_index.md")
    if not os.path.exists(index_path):
        return 0

    text = _read_file(index_path)
    lines = text.splitlines()
    out = []
    source_slugs = []
    i = 0

    # First pass: collect source org's contact slugs and remove source org section
    while i < len(lines):
        line = lines[i]
        h2 = re.match(r'^## (.+)', line)
        if h2 and h2.group(1).strip().lower() == source.lower():
            # Found source org section — collect slugs
            i += 1
            while i < len(lines) and not lines[i].startswith('##'):
                slug_line = lines[i].strip()
                if slug_line and not slug_line.startswith('#'):
                    source_slugs.append(slug_line)
                i += 1
            # Don't add source org section to output (it's deleted)
        else:
            out.append(line)
            i += 1

    if not source_slugs:
        return 0

    # Second pass: add source slugs under target org section
    final = []
    i = 0
    target_found = False

    while i < len(out):
        line = out[i]
        h2 = re.match(r'^## (.+)', line)
        if h2 and h2.group(1).strip().lower() == target.lower():
            # Found target org section
            final.append(line)
            target_found = True
            i += 1
            # Add all existing target slugs
            while i < len(out) and not out[i].startswith('##'):
                final.append(out[i])
                i += 1
            # Add source slugs
            for slug in source_slugs:
                final.append(slug)
        else:
            final.append(line)
            i += 1

    # If target org section doesn't exist, create it
    if not target_found:
        final.append(f"\n## {target}")
        for slug in source_slugs:
            final.append(slug)

    _write_file(index_path, '\n'.join(final))
    return len(source_slugs)


def _merge_people_files(source: str, target: str) -> int:
    """Update Company field from source to target in all people/*.md files.

    Returns count of people files updated.
    """
    if not os.path.isdir(PEOPLE_ROOT):
        return 0

    count = 0
    for fname in os.listdir(PEOPLE_ROOT):
        if not fname.endswith('.md'):
            continue

        path = os.path.join(PEOPLE_ROOT, fname)
        try:
            text = _read_file(path)
            lines = text.splitlines()
            updated = False

            for i, line in enumerate(lines):
                # Match Company/Organization/Org field
                m = re.match(r'^-?\s*\*\*(Company|Organization|Org):\*\*\s*(.+)', line.strip(), re.IGNORECASE)
                if m:
                    field_name = m.group(1)
                    org_val = m.group(2).strip()
                    if org_val.lower() == source.lower():
                        lines[i] = f"- **{field_name}:** {target}"
                        updated = True
                        break

            if updated:
                _write_file(path, '\n'.join(lines))
                count += 1
        except Exception:
            # Skip files that can't be read/written
            pass

    return count


def _merge_email_log(source: str, target: str) -> int:
    """Update orgMatch field from source to target in email_log.json.

    Returns count of email entries updated.
    """
    if not os.path.exists(EMAIL_LOG_PATH):
        return 0

    log_data = load_email_log()
    emails = log_data.get('emails', [])
    count = 0

    for email in emails:
        if email.get('orgMatch', '').lower() == source.lower():
            email['orgMatch'] = target
            count += 1

    if count > 0:
        save_email_log(log_data)

    return count


def _merge_briefs(source: str, target: str) -> int:
    """Re-key briefs from 'source::FundName' to 'target::FundName' in briefs.json.

    Returns count of briefs re-keyed.
    """
    briefs_data = _load_briefs()
    prospect_briefs = briefs_data.get('prospect', {})
    count = 0
    keys_to_rekey = []

    # Find all keys starting with source org
    for key in list(prospect_briefs.keys()):
        parts = key.split('::')
        if len(parts) >= 2 and parts[0].lower() == source.lower():
            keys_to_rekey.append(key)

    # Re-key them
    for old_key in keys_to_rekey:
        parts = old_key.split('::', 1)
        new_key = f"{target}::{parts[1]}"
        prospect_briefs[new_key] = prospect_briefs.pop(old_key)
        count += 1

    if count > 0:
        _save_briefs(briefs_data)

    return count


def _merge_prospect_notes(source: str, target: str) -> int:
    """Re-key prospect notes from 'source::FundName' to 'target::FundName'.

    Returns count of note entries re-keyed.
    """
    if not os.path.exists(PROSPECT_NOTES_PATH):
        return 0

    with open(PROSPECT_NOTES_PATH, 'r', encoding='utf-8') as f:
        notes_data = json.load(f)

    count = 0
    keys_to_rekey = []

    for key in list(notes_data.keys()):
        parts = key.split('::')
        if len(parts) >= 2 and parts[0].lower() == source.lower():
            keys_to_rekey.append(key)

    for old_key in keys_to_rekey:
        parts = old_key.split('::', 1)
        new_key = f"{target}::{parts[1]}"
        notes_data[new_key] = notes_data.pop(old_key)
        count += len(notes_data[new_key])

    if keys_to_rekey:
        with open(PROSPECT_NOTES_PATH, 'w', encoding='utf-8') as f:
            json.dump(notes_data, f, indent=2, ensure_ascii=False)

    return count


def _merge_prospect_meetings(source: str, target: str) -> int:
    """Re-key prospect meetings from 'source::FundName' to 'target::FundName'.

    Returns count of meeting entries re-keyed.
    """
    if not os.path.exists(PROSPECT_MEETINGS_PATH):
        return 0

    with open(PROSPECT_MEETINGS_PATH, 'r', encoding='utf-8') as f:
        meetings_data = json.load(f)

    count = 0
    keys_to_rekey = []

    for key in list(meetings_data.keys()):
        parts = key.split('::')
        if len(parts) >= 2 and parts[0].lower() == source.lower():
            keys_to_rekey.append(key)

    for old_key in keys_to_rekey:
        parts = old_key.split('::', 1)
        new_key = f"{target}::{parts[1]}"
        meetings_data[new_key] = meetings_data.pop(old_key)
        count += len(meetings_data[new_key])

    if keys_to_rekey:
        with open(PROSPECT_MEETINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(meetings_data, f, indent=2, ensure_ascii=False)

    return count
