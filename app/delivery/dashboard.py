"""
Flask app — productivity dashboard (port 3001) + CRM blueprint.
"""

import os
import sys
import re
import json
import glob as globmod

# Allow imports from app/
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from datetime import date, datetime
from flask import Flask, Blueprint, jsonify, request, render_template, redirect, url_for, abort
from sources.crm_reader import (
    load_prospects, load_offerings, get_fund_summary, get_fund_summary_all,
    load_crm_config, get_organization, write_organization, load_organizations,
    get_contacts_for_org, create_person_file, update_contact_fields,
    get_prospects_for_org, get_prospect, write_prospect, update_prospect_field,
    load_unmatched, remove_unmatched, add_unmatched,
    _parse_currency, load_person, load_tasks_by_org,
    delete_prospect, load_meeting_history, add_meeting_entry,
)

PROJECT_ROOT = os.path.dirname(APP_DIR)
TASKS_PATH = os.path.join(PROJECT_ROOT, "TASKS.md")

app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)

MEETINGS_DIR = os.path.join(PROJECT_ROOT, "meeting-summaries")
CALENDAR_PATH = os.path.join(PROJECT_ROOT, "dashboard_calendar.json")

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route('/')
def dashboard():
    all_sections = _load_tasks_grouped()
    # Dashboard shows Fundraising - Me column only
    tasks_by_section = [s for s in all_sections if s['name'] == 'Fundraising - Me']
    meetings = _load_recent_meetings(limit=10)
    calendar, calendar_stale = _load_calendar()
    config = load_crm_config()
    now = datetime.now()
    return render_template(
        'dashboard.html',
        tasks_by_section=tasks_by_section,
        meetings=meetings,
        calendar=calendar,
        calendar_stale=calendar_stale,
        config=config,
        now=now,
    )


def _load_tasks_grouped() -> list[dict]:
    """Read TASKS.md and return tasks grouped by section."""
    if not os.path.exists(TASKS_PATH):
        return []
    sections = []
    current = None
    with open(TASKS_PATH, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            m = re.match(r'^## (.+)$', line)
            if m:
                name = m.group(1).strip()
                current = {'name': name, 'tasks': []}
                sections.append(current)
                continue
            if current is not None and (line.startswith('- [ ] ') or line.startswith('- [x] ')):
                done = line.startswith('- [x] ')
                text = line[6:].strip()
                # Parse priority
                priority = 'Med'
                pm = re.match(r'\*\*\[(\w+)\]\*\*\s*', text)
                if pm:
                    priority = pm.group(1)
                    text = text[pm.end():]
                # Extract and strip **@Owner** tag (supports multi-word names like "Mike R")
                assigned_to = ''
                owner_m = re.match(r'\*\*@([^*]+)\*\*\s*', text)
                if owner_m:
                    assigned_to = owner_m.group(1).strip()
                    text = text[owner_m.end():]
                # Extract (OrgName) suffix
                org = ''
                org_m = re.search(r'\(([^)]+)\)\s*$', text)
                if org_m:
                    org = org_m.group(1).strip()
                    text = text[:org_m.start()].rstrip(' —-')
                # Strip ~~...~~ for done items
                text = re.sub(r'~~(.+?)~~', r'\1', text)
                idx = len(current['tasks'])
                current['tasks'].append({
                    'text': text,
                    'done': done,
                    'priority': priority,
                    'org': org,
                    'assigned_to': assigned_to,
                    'raw': line[6:].strip(),
                    'index': idx,
                })
    # Sort tasks within each section by priority
    pri_order = {'Hi': 0, 'Med': 1, 'Low': 2}
    for sec in sections:
        sec['tasks'].sort(key=lambda t: pri_order.get(t['priority'], 1))
    return sections


def _load_tasks() -> list[dict]:
    """Read TASKS.md and return top-level task lines (flat, for API)."""
    if not os.path.exists(TASKS_PATH):
        return []
    tasks = []
    with open(TASKS_PATH, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            if line.startswith('- [ ] ') or line.startswith('- [x] '):
                done = line.startswith('- [x] ')
                tasks.append({'text': line[6:].strip(), 'done': done})
    return tasks[:50]


def _load_recent_meetings(limit=10) -> list[dict]:
    """Load recent meeting summaries from markdown files."""
    if not os.path.isdir(MEETINGS_DIR):
        return []
    files = sorted(globmod.glob(os.path.join(MEETINGS_DIR, "*.md")), reverse=True)
    meetings = []
    for fp in files[:limit]:
        fname = os.path.basename(fp)
        # Parse date and title from filename: YYYY-MM-DD-title-slug.md
        m = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.md$', fname)
        if not m:
            continue
        meeting_date = m.group(1)
        slug = m.group(2)
        title = slug.replace('-', ' ').title()
        attendees = ''
        notion_url = ''
        with open(fp, encoding='utf-8') as f:
            for line in f:
                if line.startswith('**Attendees:**'):
                    attendees = line.split(':', 1)[1].strip()
                if line.startswith('**Source:**'):
                    um = re.search(r'\[.*?\]\((https?://[^\)]+)\)', line)
                    if um:
                        notion_url = um.group(1)
                if attendees and notion_url:
                    break
        meetings.append({
            'date': meeting_date,
            'title': title,
            'attendees': attendees,
            'url': notion_url,
            'filename': fname,
        })
    return meetings


def _load_calendar() -> tuple[list[dict], str | None]:
    """Load today's calendar from JSON file (written by update process).
    Returns (events, stale_date) where stale_date is set if the file is
    from a previous day (so the template can show a staleness warning).
    """
    if not os.path.exists(CALENDAR_PATH):
        return [], None
    try:
        mtime = os.path.getmtime(CALENDAR_PATH)
        file_date = datetime.fromtimestamp(mtime).date()
        stale = file_date if file_date != date.today() else None
        if stale:
            return [], stale.strftime('%b %-d')
        with open(CALENDAR_PATH, encoding='utf-8') as f:
            return json.load(f), None
    except (json.JSONDecodeError, IOError):
        return [], None


@app.route('/api/task/complete', methods=['POST'])
def task_complete():
    data = request.get_json(force=True)
    task_text = data.get('text', '').strip()
    if not task_text or not os.path.exists(TASKS_PATH):
        return jsonify({'ok': False}), 400
    with open(TASKS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(f'- [ ] {task_text}', f'- [x] {task_text}', 1)
    with open(TASKS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'ok': True})


@app.route('/api/task/add', methods=['POST'])
def task_add():
    data = request.get_json(force=True)
    text = data.get('text', '').strip()
    priority = data.get('priority', 'Med').strip()
    section = data.get('section', 'Active').strip()
    if not text or not os.path.exists(TASKS_PATH):
        return jsonify({'ok': False}), 400
    with open(TASKS_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    new_line = f'- [ ] **[{priority}]** {text}\n'
    target = f'## {section}'
    inserted = False
    for i, ln in enumerate(lines):
        if ln.strip() == target:
            lines.insert(i + 1, new_line)
            inserted = True
            break
    if not inserted:
        lines.append(new_line)
    with open(TASKS_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# CRM Blueprint
# ---------------------------------------------------------------------------

crm_bp = Blueprint('crm', __name__, url_prefix='/crm')

EDITABLE_FIELDS = {
    'stage', 'urgency', 'target', 'assigned_to', 'notes', 'closing'
}


# --- KB people ---

def parse_kb_person_file(path: str) -> dict:
    """Parse a memory/people/*.md file into a person dict."""
    slug = os.path.splitext(os.path.basename(path))[0]
    # Convert slug to Title Case as fallback name
    name_fallback = ' '.join(w.capitalize() for w in slug.replace('-', ' ').split())
    fields = {'name': name_fallback, 'org': '', 'title': '', 'email': '', 'phone': ''}
    field_map = {
        'name':         'name',
        'organization': 'org',
        'org':          'org',
        'title':        'title',
        'role':         'title',   # actual files use Role not Title
        'email':        'email',
        'phone':        'phone',
    }
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                # Parse # Heading as name
                h1 = re.match(r'^#\s+(.+)', line.strip())
                if h1:
                    fields['name'] = h1.group(1).strip()
                    continue
                m = re.match(r'-\s+\*\*(\w+):\*\*\s*(.*)', line.strip())
                if m:
                    key = m.group(1).lower()
                    val = m.group(2).strip()
                    if key in field_map and val:
                        fields[field_map[key]] = val
    except Exception:
        pass
    return fields


@crm_bp.route('/api/kb-people')
def api_kb_people():
    q = request.args.get('q', '').lower().strip()
    config = load_crm_config()
    arec_team = {name.lower() for name in config.get('team', [])}
    people_dir = os.path.join(PROJECT_ROOT, 'memory', 'people')
    results = []
    if os.path.isdir(people_dir):
        for fname in sorted(os.listdir(people_dir)):
            if not fname.endswith('.md'):
                continue
            path = os.path.join(people_dir, fname)
            person = parse_kb_person_file(path)
            if person['name'].lower() in arec_team:
                continue
            if not q or q in person['name'].lower():
                results.append(person)
    results.sort(key=lambda p: p['name'].lower())
    return jsonify(results)


# --- Page routes ---

@crm_bp.route('/')
@crm_bp.route('')
def pipeline():
    config = load_crm_config()
    offerings = load_offerings()
    return render_template('crm_pipeline.html', config=config, offerings=offerings)


@crm_bp.route('/org/<path:name>')
def org_detail(name):
    config = load_crm_config()
    offerings = load_offerings()
    return render_template('crm_org_detail.html', org_name=name, config=config, offerings=offerings)


@crm_bp.route('/prospect/<offering>/<path:org>')
def prospect_edit(offering, org):
    prospect = get_prospect(org, offering)
    if not prospect:
        abort(404)
    config = load_crm_config()
    contacts = get_contacts_for_org(org)
    return render_template('crm_prospect_edit.html',
                           prospect=prospect,
                           config=config,
                           contacts=contacts,
                           offering=offering,
                           org=org)


# --- Data API ---

@crm_bp.route('/api/offerings')
def api_offerings():
    return jsonify(load_offerings())


@crm_bp.route('/api/prospects')
def api_prospects():
    offering = request.args.get('offering', '')
    include_closed = request.args.get('include_closed', 'false').lower() == 'true'
    prospects = load_prospects(offering if offering else None)
    if not include_closed:
        excluded = {'8. Closed', '0. Not Pursuing', '0. Declined'}
        prospects = [p for p in prospects if p.get('Stage', '') not in excluded]

    # Enrich with tasks from TASKS.md
    tasks_by_org = load_tasks_by_org()
    for p in prospects:
        org_name = p.get('org', '')
        org_tasks = tasks_by_org.get(org_name, [])
        # Flat string for display/backward compat
        if org_tasks:
            p['Tasks'] = ' | '.join(
                f"[@{t['owner']}] {t['task']}" for t in org_tasks
            )
        else:
            p['Tasks'] = ''
        # Structured data for modal editing
        p['_tasks'] = org_tasks

    return jsonify(prospects)


@crm_bp.route('/api/fund-summary')
def api_fund_summary():
    offering = request.args.get('offering', '')
    if offering:
        return jsonify(get_fund_summary(offering))
    return jsonify(get_fund_summary_all())


# --- Inline field edit ---

@crm_bp.route('/api/prospect/field', methods=['PATCH'])
def api_patch_prospect_field():
    data = request.get_json(force=True)
    org = data.get('org', '').strip()
    offering = data.get('offering', '').strip()
    field = data.get('field', '').strip().lower()
    value = data.get('value', '').strip()

    if not org or not offering or not field:
        return jsonify({'error': 'org, offering, and field are required'}), 400

    if field not in EDITABLE_FIELDS:
        return jsonify({'error': f'Field "{field}" is not editable'}), 400

    config = load_crm_config()
    if field == 'stage' and value not in config['stages'] and value != '':
        return jsonify({'error': f'Invalid stage: {value}'}), 400
    if field == 'urgency' and value not in config['urgency_levels'] and value != '':
        return jsonify({'error': f'Invalid urgency: {value}'}), 400
    if field == 'assigned_to' and value != '':
        valid_names = set(config['team'])
        valid_names.update(m['short'] for m in config.get('team_map', []))
        if value not in valid_names:
            return jsonify({'error': f'Invalid team member: {value}'}), 400
    if field == 'closing' and value not in config['closing_options'] and value != '':
        return jsonify({'error': f'Invalid closing option: {value}'}), 400

    if field == 'target':
        # Normalize to display format
        parsed = _parse_currency(value)
        value = f"${parsed:,.0f}" if parsed else '$0'

    update_prospect_field(org, offering, field, value)
    updated = get_prospect(org, offering)
    return jsonify(updated)


# --- Org API ---

@crm_bp.route('/api/org/<path:name>', methods=['GET'])
def api_org_get(name):
    org = get_organization(name)
    if not org:
        # Return empty org structure rather than 404 (org may exist in prospects but not orgs)
        org = {'name': name, 'Type': '', 'Notes': ''}
    contacts = get_contacts_for_org(name)
    prospects = get_prospects_for_org(name)
    return jsonify({
        'org': org,
        'contacts': contacts,
        'prospects': prospects,
    })


@crm_bp.route('/api/org/<path:name>', methods=['PATCH'])
def api_org_patch(name):
    data = request.get_json(force=True)
    allowed = {'type', 'notes'}
    payload = {}
    if 'type' in data:
        payload['Type'] = data['type']
    if 'notes' in data:
        payload['Notes'] = data['notes']
    if not payload:
        return jsonify({'error': 'No valid fields to update'}), 400

    # Ensure org exists in organizations.md first
    existing = get_organization(name)
    if existing:
        merged = {**existing, **payload}
    else:
        merged = {'name': name, 'Type': '', 'Notes': '', **payload}

    write_organization(name, merged)
    return jsonify(get_organization(name) or merged)


# --- Contact API ---

@crm_bp.route('/api/contact', methods=['POST'])
def api_contact_create():
    data = request.get_json(force=True)
    name = data.get('name', '').strip()
    org = data.get('org', '').strip()
    if not name or not org:
        return jsonify({'error': 'name and org are required'}), 400

    email = data.get('email', '').strip()
    role = data.get('role', '').strip()
    person_type = data.get('type', 'investor').strip()

    slug = create_person_file(name, org, email, role, person_type)
    person = load_person(slug)
    return jsonify(person), 201


@crm_bp.route('/api/contact/<path:org_and_name>', methods=['PATCH'])
def api_contact_patch(org_and_name):
    # URL format: /api/contact/<org>/<name>
    # Split on last slash
    parts = org_and_name.rsplit('/', 1)
    if len(parts) != 2:
        return jsonify({'error': 'URL must be /api/contact/<org>/<name>'}), 400
    org, name = parts[0], parts[1]
    data = request.get_json(force=True)
    allowed_fields = {'role', 'email', 'phone', 'title'}
    payload = {k: v for k, v in data.items() if k in allowed_fields}
    if not payload:
        return jsonify({'error': 'No valid fields to update'}), 400
    success = update_contact_fields(org, name, payload)
    if not success:
        return jsonify({'error': 'Contact not found'}), 404
    return jsonify({'ok': True})


# --- Prospect full save (edit page) ---

@crm_bp.route('/api/prospect/save', methods=['POST'])
def api_prospect_save():
    data = request.get_json(force=True)
    org = data.get('org', '').strip()
    offering = data.get('offering', '').strip()
    fields = data.get('fields', {})
    if not org or not offering:
        return jsonify({'error': 'org and offering are required'}), 400
    if not get_prospect(org, offering):
        return jsonify({'error': 'Prospect not found'}), 404
    for field, value in fields.items():
        update_prospect_field(org, offering, field, str(value))
    # Ensure last_touch is set to today
    update_prospect_field(org, offering, 'last_touch', date.today().isoformat())
    return jsonify({'status': 'ok'})


# --- Prospect create ---

@crm_bp.route('/api/prospect', methods=['POST'])
def api_prospect_create():
    data = request.get_json(force=True)
    org = data.get('org', '').strip()
    offering = data.get('offering', '').strip()
    if not org or not offering:
        return jsonify({'error': 'org and offering are required'}), 400

    # Don't create duplicate
    existing = get_prospect(org, offering)
    if existing:
        return jsonify({'error': 'Prospect already exists for this org + offering'}), 409

    new_prospect = {
        'org': org,
        'offering': offering,
        'Stage': data.get('stage', '1. Prospect'),
        'Target': data.get('target', '$0'),
        'Committed': '$0',
        'Primary Contact': '',
        'Closing': '',
        'Urgency': '',
        'Assigned To': '',
        'Notes': '',
        'Last Touch': '',
    }
    write_prospect(org, offering, new_prospect)
    created = get_prospect(org, offering)
    return jsonify(created), 201


@crm_bp.route('/api/prospect', methods=['DELETE'])
def api_prospect_delete():
    data = request.get_json(force=True)
    org = data.get('org', '').strip()
    offering = data.get('offering', '').strip()
    if not org or not offering:
        return jsonify({'error': 'org and offering required'}), 400
    try:
        delete_prospect(org, offering)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- Unmatched review ---

@crm_bp.route('/api/unmatched', methods=['GET'])
def api_unmatched_list():
    return jsonify(load_unmatched())


@crm_bp.route('/api/unmatched/resolve', methods=['POST'])
def api_unmatched_resolve():
    data = request.get_json(force=True)
    email = data.get('email', '').strip()
    org_name = data.get('org_name', '').strip()
    if not email or not org_name:
        return jsonify({'error': 'email and org_name required'}), 400
    # Create a stub person file for the newly matched contact
    participant_name = data.get('participant_name', '').strip()
    if participant_name:
        create_person_file(
            name=participant_name,
            org=org_name,
            email=email,
            role='',
            person_type='investor',
        )
    remove_unmatched(email)
    return jsonify({'ok': True})


@crm_bp.route('/api/unmatched/<path:email>', methods=['DELETE'])
def api_unmatched_dismiss(email):
    remove_unmatched(email)
    return jsonify({'ok': True})


# --- Org list (for dropdowns) ---

@crm_bp.route('/api/orgs')
def api_orgs():
    orgs = load_organizations()
    return jsonify([o['name'] for o in orgs])


# --- Meeting History ---

@crm_bp.route('/api/org/<path:name>/meetings', methods=['GET'])
def api_org_meetings(name):
    meetings = load_meeting_history(name)
    return jsonify(meetings)


@crm_bp.route('/api/org/<path:name>/meetings', methods=['POST'])
def api_org_meeting_add(name):
    data = request.get_json(force=True)
    add_meeting_entry(
        org=name,
        date=data.get('date', ''),
        title=data.get('title', ''),
        attendees=data.get('attendees', ''),
        source=data.get('source', 'manual'),
        notion_url=data.get('notion_url', ''),
    )
    return jsonify({'ok': True})


app.register_blueprint(crm_bp)


# ---------------------------------------------------------------------------
# Tasks Blueprint
# ---------------------------------------------------------------------------

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

TASK_SECTIONS = ['Fundraising - Me', 'Waiting On', 'Work', 'Personal']


def _parse_task_line(line: str, section: str) -> dict:
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

    # Completion date
    completion_date = None
    cdm = re.search(r'\s*—\s*completed\s+(\d{4}-\d{2}-\d{2})', text)
    if cdm:
        completion_date = cdm.group(1)
        text = text[:cdm.start()]

    # Context (after —)
    context = ''
    assigned_to = None
    di = text.find(' — ')
    if di >= 0:
        context = text[di + 3:]
        text = text[:di]

    # for: tag (Waiting On section)
    if section == 'Waiting On' and context:
        fm = re.search(r'for:\s*(.+)', context)
        if fm:
            assigned_to = fm.group(1).strip()

    # **@Name** owner tag (supports multi-word names like "Mike R")
    if assigned_to is None:
        om = re.match(r'\*\*@([^*]+)\*\*\s*', text)
        if om:
            assigned_to = om.group(1)
            text = text[om.end():]

    # Extract (OrgName) suffix
    org = ''
    org_m = re.search(r'\(([^)]+)\)\s*$', text)
    if org_m:
        org = org_m.group(1).strip()
        text = text[:org_m.start()].rstrip(' —-')

    # Strip ~~strikethrough~~
    text = re.sub(r'~~(.+?)~~', r'\1', text)

    return {
        'text': text.strip(),
        'priority': priority,
        'context': context,
        'assigned_to': assigned_to,
        'org': org,
        'complete': done,
        'completion_date': completion_date,
        'raw': raw,
    }


def _load_tasks_full() -> dict:
    """
    Returns {section_name: [task_dicts_with_index]}.
    Sections: Fundraising - Me, Waiting On, Work, Personal (+ Done).
    'index' = 0-based position of that task within the section.
    """
    if not os.path.exists(TASKS_PATH):
        return {s: [] for s in TASK_SECTIONS + ['Done']}

    result = {}
    current_name = None
    current_tasks = []

    def flush():
        if current_name is not None:
            result[current_name] = current_tasks[:]

    with open(TASKS_PATH, encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^## (.+)$', line.rstrip())
            if m:
                flush()
                current_name = m.group(1).strip()
                current_tasks = []
                continue
            if current_name and (line.startswith('- [ ] ') or line.startswith('- [x] ')):
                task = _parse_task_line(line, current_name)
                task['index'] = len(current_tasks)
                task['section'] = current_name
                current_tasks.append(task)
    flush()

    # Ensure all canonical sections are present
    for s in TASK_SECTIONS + ['Done']:
        if s not in result:
            result[s] = []
    return result


def _read_task_lines() -> list:
    if not os.path.exists(TASKS_PATH):
        return []
    with open(TASKS_PATH, 'r', encoding='utf-8') as f:
        return f.readlines()


def _write_task_file(lines: list) -> None:
    with open(TASKS_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def _find_task_line(lines: list, section: str, index: int):
    """
    Return the file line index of the task at position [index] within [section].
    Returns -1 if not found.
    """
    in_section = False
    count = 0
    for i, ln in enumerate(lines):
        m = re.match(r'^## (.+)$', ln.rstrip())
        if m:
            in_section = m.group(1).strip() == section
            continue
        if in_section and (ln.startswith('- [ ] ') or ln.startswith('- [x] ')):
            if count == index:
                return i
            count += 1
    return -1


def _format_task_line(text: str, priority: str, context: str,
                      assigned_to: str, section: str, done: bool = False,
                      completion_date: str = None) -> str:
    """Serialize a task dict back to a markdown line."""
    checkbox = '- [x] ' if done else '- [ ] '
    line = f'**[{priority}]** '
    # Always embed owner as **@Name** prefix when assigned
    if assigned_to:
        line += f'**@{assigned_to}** '
    line += text
    if context:
        line += f' — {context}'
    if done and completion_date:
        line += f' — completed {completion_date}'
    return checkbox + line + '\n'


# --- Routes ---

@tasks_bp.route('/', methods=['GET'])
@tasks_bp.route('', methods=['GET'])
def tasks_page():
    config = load_crm_config()
    return render_template('tasks/tasks.html', config=config)


@tasks_bp.route('/api/tasks', methods=['GET'])
def api_tasks():
    return jsonify(_load_tasks_full())


@tasks_bp.route('/api/task', methods=['POST'])
def api_task_create():
    data = request.get_json(force=True)
    section = data.get('section', '').strip()
    text = data.get('text', '').strip()
    priority = data.get('priority', 'Med').strip()
    context = data.get('context', '').strip()
    assigned_to = data.get('assigned_to', '').strip()

    if not text or section not in TASK_SECTIONS:
        return jsonify({'ok': False, 'error': 'text and valid section required'}), 400

    new_line = _format_task_line(text, priority, context, assigned_to, section)

    lines = _read_task_lines()
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
    _write_task_file(lines)
    return jsonify({'ok': True})


@tasks_bp.route('/api/task/<section>/<int:index>', methods=['PUT'])
def api_task_update(section, index):
    data = request.get_json(force=True)
    new_section = data.get('section', section).strip()
    text = data.get('text', '').strip()
    priority = data.get('priority', 'Med').strip()
    context = data.get('context', '').strip()
    assigned_to = data.get('assigned_to', '').strip()

    if not text:
        return jsonify({'ok': False, 'error': 'text required'}), 400

    lines = _read_task_lines()
    li = _find_task_line(lines, section, index)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404

    original = lines[li]
    was_done = original.startswith('- [x] ')
    cdm = re.search(r'—\s*completed\s+(\d{4}-\d{2}-\d{2})', original)
    completion_date = cdm.group(1) if cdm else None

    new_line = _format_task_line(text, priority, context, assigned_to,
                                  new_section, done=was_done,
                                  completion_date=completion_date)

    if new_section == section:
        lines[li] = new_line
        _write_task_file(lines)
    else:
        # Move: remove from current section, insert into new section
        lines.pop(li)
        target = f'## {new_section}'
        inserted = False
        for i, ln in enumerate(lines):
            if ln.strip() == target:
                lines.insert(i + 1, new_line)
                inserted = True
                break
        if not inserted:
            lines.append(f'\n## {new_section}\n')
            lines.append(new_line)
        _write_task_file(lines)

    return jsonify({'ok': True})


@tasks_bp.route('/api/task/<section>/<int:index>', methods=['DELETE'])
def api_task_delete(section, index):
    lines = _read_task_lines()
    li = _find_task_line(lines, section, index)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404
    lines.pop(li)
    _write_task_file(lines)
    return jsonify({'ok': True})


@tasks_bp.route('/api/task/<section>/<int:index>/complete', methods=['POST'])
def api_task_complete_new(section, index):
    today = date.today().isoformat()
    lines = _read_task_lines()
    li = _find_task_line(lines, section, index)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404
    ln = lines[li]
    if not ln.startswith('- [ ] '):
        return jsonify({'ok': False, 'error': 'task already complete'}), 400
    ln = '- [x] ' + ln[6:]
    # Append completion date if not already there
    ln = ln.rstrip()
    if 'completed' not in ln:
        ln += f' — completed {today}'
    lines[li] = ln + '\n'
    _write_task_file(lines)
    return jsonify({'ok': True})


@tasks_bp.route('/api/task/<section>/<int:index>/restore', methods=['POST'])
def api_task_restore(section, index):
    lines = _read_task_lines()
    li = _find_task_line(lines, section, index)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404
    ln = lines[li]
    if not ln.startswith('- [x] '):
        return jsonify({'ok': False, 'error': 'task not complete'}), 400
    ln = '- [ ] ' + ln[6:]
    # Strip completion date
    ln = re.sub(r'\s*—\s*completed\s+\d{4}-\d{2}-\d{2}', '', ln.rstrip())
    lines[li] = ln + '\n'
    _write_task_file(lines)
    return jsonify({'ok': True})


app.register_blueprint(tasks_bp)


if __name__ == '__main__':
    app.run(port=3001, debug=True)
