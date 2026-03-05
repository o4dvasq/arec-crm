"""
CRM data reader/writer for all markdown files in crm/ and memory/people/.
All downstream consumers import from here. No parsing logic elsewhere.
"""

import os
import re
import json
from datetime import date, datetime, timedelta

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app
PROJECT_ROOT = os.path.dirname(APP_ROOT)  # .../ClaudeProductivity
CRM_ROOT = os.path.join(PROJECT_ROOT, "crm")
MEMORY_ROOT = os.path.join(PROJECT_ROOT, "memory")
PEOPLE_ROOT = os.path.join(MEMORY_ROOT, "people")

# Field write order for prospects
PROSPECT_FIELD_ORDER = [
    "Stage", "Target", "Primary Contact",
    "Closing", "Urgency", "Assigned To", "Notes", "Last Touch"
]

EDITABLE_FIELDS = {
    'stage', 'urgency', 'target', 'assigned_to',
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
        formatted = f"{val:g}"
        return f"${formatted}B"
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

    # Parse team entries: "Short | Full Name" format
    raw_team = sections.get('AREC Team', [])
    team_list = []  # list of full names (backward compat)
    team_map = []   # list of {short, full} dicts for UI
    for entry in raw_team:
        if '|' in entry:
            short, full = [s.strip() for s in entry.split('|', 1)]
        else:
            full = entry.strip()
            short = full.split()[0]  # fallback: first name
        team_list.append(full)
        team_map.append({'short': short, 'full': full})

    return {
        'stages': sections.get('Pipeline Stages', []),
        'terminal_stages': sections.get('Terminal Stages', []),
        'org_types': sections.get('Organization Types', []),
        'closing_options': sections.get('Closing Options', []),
        'urgency_levels': sections.get('Urgency Levels', []),
        'team': team_list,
        'team_map': team_map,
    }


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
    """Update fields for an existing org. Preserves all other orgs."""
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
            # Skip existing field lines
            while i < len(lines) and lines[i].strip().startswith('-'):
                i += 1
            # Write new fields
            for key in ('Type', 'Notes'):
                val = data.get(key, data.get(key.lower(), ''))
                out.append(f"- **{key}:** {val}")
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
        for key in ('Type', 'Notes'):
            val = data.get(key, data.get(key.lower(), ''))
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
    """Returns {org_name: [slug, ...]}"""
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
    field_title = next(
        (k for k in PROSPECT_FIELD_ORDER if k.lower() == field_normalized),
        field
    )
    prospect[field_title] = value
    # Auto-update last touch
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
    Only open tasks (unchecked) from Active and Waiting On sections are included.
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

            # Extract owner: **@Name** (supports multi-word names like "Mike R")
            owner_match = re.search(r'\*\*@([^*]+)\*\*', stripped)
            owner = owner_match.group(1).strip() if owner_match else 'Oscar'

            # Extract org: (OrgName) at end of line
            org_match = re.search(r'\(([^)]+)\)\s*$', stripped)
            if not org_match:
                task_index += 1
                continue  # Not a CRM task

            org_name = org_match.group(1).strip()

            # Extract task description: strip checkbox, priority, owner tag, and trailing (OrgName)
            desc = stripped
            desc = re.sub(r'^- \[ \]\s*\*\*\[\w+\]\*\*\s*', '', desc)  # Remove checkbox + priority
            desc = re.sub(r'\*\*@[^*]+\*\*\s*', '', desc)               # Remove owner tag (supports multi-word names)
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
