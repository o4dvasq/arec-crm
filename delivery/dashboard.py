"""
Flask app — productivity dashboard (port 3001) + CRM blueprint.
"""

import os
import sys

# Allow imports from app/
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from datetime import date
from flask import Flask, Blueprint, jsonify, request, render_template, redirect, url_for, abort
from sources.crm_reader import (
    load_prospects, load_offerings, get_fund_summary, get_fund_summary_all,
    load_crm_config, get_organization, write_organization, load_organizations,
    get_contacts_for_org, create_person_file, update_contact_fields,
    get_prospects_for_org, get_prospect, write_prospect, update_prospect_field,
    load_unmatched, remove_unmatched, add_unmatched,
    _parse_currency, load_person,
)

PROJECT_ROOT = os.path.dirname(APP_DIR)
TASKS_PATH = os.path.join(PROJECT_ROOT, "TASKS.md")

app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)

# ---------------------------------------------------------------------------
# Dashboard (stub)
# ---------------------------------------------------------------------------

@app.route('/')
def dashboard():
    tasks = _load_tasks()
    return render_template('dashboard.html', tasks=tasks)


def _load_tasks() -> list[dict]:
    """Read TASKS.md and return top-level task lines."""
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


# ---------------------------------------------------------------------------
# CRM Blueprint
# ---------------------------------------------------------------------------

crm_bp = Blueprint('crm', __name__, url_prefix='/crm')

EDITABLE_FIELDS = {
    'stage', 'urgency', 'target', 'assigned_to', 'next_action', 'notes', 'closing'
}


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
        excluded = {'9. Closed', '0. Not Pursuing', 'Declined'}
        prospects = [p for p in prospects if p.get('Stage', '') not in excluded]
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
    if field == 'assigned_to' and value not in config['team'] and value != '':
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
        'Next Action': '',
        'Last Touch': '',
    }
    write_prospect(org, offering, new_prospect)
    created = get_prospect(org, offering)
    return jsonify(created), 201


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


app.register_blueprint(crm_bp)


if __name__ == '__main__':
    app.run(port=3001, debug=True)
