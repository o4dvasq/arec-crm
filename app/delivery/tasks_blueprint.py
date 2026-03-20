"""
tasks_blueprint.py — Flask Tasks blueprint (/tasks routes).
Extracted from dashboard.py for maintainability.
"""

import os
import sys
import re
from datetime import date
from flask import Blueprint, jsonify, request, render_template

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

PROJECT_ROOT = os.path.dirname(_APP_DIR)
TASKS_PATH = os.path.join(PROJECT_ROOT, "TASKS.md")

from sources.crm_reader import load_crm_config, get_tasks_for_prospect, add_prospect_task, normalize_team_name
from sources.memory_reader import _parse_task_line, _format_task_line

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


def _normalize_assigned_to(raw: str) -> str:
    """Delegate to shared normalize_team_name in crm_reader."""
    return normalize_team_name(raw)


# ---------------------------------------------------------------------------
# Task file helpers
# ---------------------------------------------------------------------------

def _load_tasks_full() -> dict:
    """Parse TASKS.md → {'open': [...], 'done': [...]}. Each task includes 'index'."""
    if not os.path.exists(TASKS_PATH):
        return {'open': [], 'done': []}

    open_tasks = []
    done_tasks = []
    in_done = False

    with open(TASKS_PATH, encoding='utf-8') as f:
        for line in f:
            stripped = line.rstrip()
            if re.match(r'^## Done', stripped):
                in_done = True
                continue
            if re.match(r'^## ', stripped):
                # Any other section header — skip
                continue
            if line.startswith('- [ ] ') or line.startswith('- [x] '):
                if in_done:
                    task = _parse_task_line(line)
                    task['index'] = len(done_tasks)
                    done_tasks.append(task)
                else:
                    task = _parse_task_line(line)
                    task['index'] = len(open_tasks)
                    open_tasks.append(task)

    return {'open': open_tasks, 'done': done_tasks}


def _read_task_lines() -> list:
    if not os.path.exists(TASKS_PATH):
        return []
    with open(TASKS_PATH, 'r', encoding='utf-8') as f:
        return f.readlines()


def _write_task_file(lines: list) -> None:
    with open(TASKS_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def _find_task_line(lines: list, index: int, done: bool = False) -> int:
    """Find the file line number for the nth task (0-based).

    If done=False: counts open tasks before ## Done.
    If done=True: counts tasks after ## Done.
    """
    in_done_section = False
    count = 0
    for i, ln in enumerate(lines):
        if re.match(r'^## Done', ln.rstrip()):
            in_done_section = True
            continue
        if re.match(r'^## ', ln.rstrip()):
            in_done_section = False
            continue
        if in_done_section == done and (ln.startswith('- [ ] ') or ln.startswith('- [x] ')):
            if count == index:
                return i
            count += 1
    return -1


def _find_done_insertion_point(lines: list) -> int:
    """Return the line index immediately after '## Done' header."""
    for i, ln in enumerate(lines):
        if re.match(r'^## Done', ln.rstrip()):
            return i + 1
    return len(lines)


def _find_open_insertion_point(lines: list) -> int:
    """Return the line index just before '## Done' (to append open tasks)."""
    for i, ln in enumerate(lines):
        if re.match(r'^## Done', ln.rstrip()):
            # Insert before blank line + ## Done — find first non-blank before it
            return i
    return len(lines)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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
    text = data.get('text', '').strip()
    priority = data.get('priority', 'Med').strip()
    context = data.get('context', '').strip()
    assigned_to = _normalize_assigned_to(data.get('assigned_to', ''))
    status = data.get('status', 'new').strip()
    org = data.get('org', '').strip()

    if not text:
        return jsonify({'ok': False, 'error': 'text required'}), 400

    new_line = _format_task_line(text, priority, context, assigned_to, status=status, org=org)

    lines = _read_task_lines()
    insert_at = _find_open_insertion_point(lines)
    lines.insert(insert_at, new_line)
    _write_task_file(lines)
    return jsonify({'ok': True})


@tasks_bp.route('/api/task/<int:index>', methods=['PUT'])
def api_task_update(index):
    data = request.get_json(force=True)
    text = data.get('text', '').strip()
    priority = data.get('priority', 'Med').strip()
    context = data.get('context', '').strip()
    assigned_to = _normalize_assigned_to(data.get('assigned_to', ''))
    status = data.get('status', 'open').strip()
    org = data.get('org', '').strip()

    if not text:
        return jsonify({'ok': False, 'error': 'text required'}), 400

    lines = _read_task_lines()
    li = _find_task_line(lines, index)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404

    original = lines[li]
    was_done = original.startswith('- [x] ')
    cdm = re.search(r'—\s*completed\s+(\d{4}-\d{2}-\d{2})', original)
    completion_date = cdm.group(1) if cdm else None

    new_line = _format_task_line(text, priority, context, assigned_to,
                                  done=was_done, completion_date=completion_date,
                                  status=status, org=org)
    lines[li] = new_line
    _write_task_file(lines)
    return jsonify({'ok': True})


@tasks_bp.route('/api/task/<int:index>', methods=['DELETE'])
def api_task_delete(index):
    lines = _read_task_lines()
    li = _find_task_line(lines, index)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404
    lines.pop(li)
    _write_task_file(lines)
    return jsonify({'ok': True})


@tasks_bp.route('/api/task/<int:index>/complete', methods=['POST'])
def api_task_complete_new(index):
    today = date.today().isoformat()
    lines = _read_task_lines()
    li = _find_task_line(lines, index)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404
    ln = lines[li]
    if not ln.startswith('- [ ] '):
        return jsonify({'ok': False, 'error': 'task already complete'}), 400

    ln = '- [x] ' + ln[6:].rstrip()
    if 'completed' not in ln:
        ln += f' — completed {today}'
    ln += '\n'

    # Move: remove from open list, append to Done section
    lines.pop(li)
    insert_at = _find_done_insertion_point(lines)
    lines.insert(insert_at, ln)
    _write_task_file(lines)
    return jsonify({'ok': True})


@tasks_bp.route('/api/task/<int:index>/restore', methods=['POST'])
def api_task_restore(index):
    lines = _read_task_lines()
    li = _find_task_line(lines, index, done=True)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404
    ln = lines[li]
    if not ln.startswith('- [x] '):
        return jsonify({'ok': False, 'error': 'task not complete'}), 400

    ln = '- [ ] ' + ln[6:]
    ln = re.sub(r'\s*—\s*completed\s+\d{4}-\d{2}-\d{2}', '', ln.rstrip())
    ln += '\n'

    # Move: remove from Done, insert before ## Done
    lines.pop(li)
    insert_at = _find_open_insertion_point(lines)
    lines.insert(insert_at, ln)
    _write_task_file(lines)
    return jsonify({'ok': True})


@tasks_bp.route('/api/task/<int:index>/status', methods=['PATCH'])
def api_task_status_update(index):
    data = request.get_json(force=True)
    new_status = data.get('status', '').strip()

    valid_statuses = ['New', 'In Progress', 'Complete']
    if new_status not in valid_statuses:
        return jsonify({'ok': False, 'error': f'status must be one of: {", ".join(valid_statuses)}'}), 400

    lines = _read_task_lines()
    li = _find_task_line(lines, index)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404

    task = _parse_task_line(lines[li])
    done = new_status == 'Complete'
    completion_date = date.today().isoformat() if done and not task['complete'] else task.get('completion_date')

    new_line = _format_task_line(
        task['text'], task['priority'], task['context'], task['assigned_to'],
        done=done, completion_date=completion_date,
        status=new_status, org=task.get('org', '')
    )

    lines[li] = new_line
    _write_task_file(lines)
    return jsonify({'ok': True, 'status': new_status})


@tasks_bp.route('/api/task/<int:index>/priority', methods=['PATCH'])
def api_task_priority_update(index):
    data = request.get_json(force=True)
    new_priority = data.get('priority', '').strip()

    valid_priorities = ['Hi', 'Med', 'Low']
    if new_priority not in valid_priorities:
        return jsonify({'ok': False, 'error': f'priority must be one of: {", ".join(valid_priorities)}'}), 400

    lines = _read_task_lines()
    li = _find_task_line(lines, index)
    if li == -1:
        return jsonify({'ok': False, 'error': 'task not found'}), 404

    task = _parse_task_line(lines[li])

    new_line = _format_task_line(
        task['text'],
        new_priority,
        task['context'],
        task['assigned_to'],
        done=task['complete'],
        completion_date=task.get('completion_date'),
        status=task.get('status', 'New'),
        org=task.get('org', '')
    )

    lines[li] = new_line
    _write_task_file(lines)
    return jsonify({'ok': True, 'priority': new_priority})


@tasks_bp.route('/api/tasks/for-org', methods=['GET'])
def api_tasks_for_org():
    """Return all open prospect tasks for a given org."""
    org = request.args.get('org', '').strip()
    if not org:
        return jsonify({'error': 'org parameter required'}), 400

    tasks = get_tasks_for_prospect(org)
    results = []
    for i, t in enumerate(tasks):
        results.append({
            'id': i,
            'text': t['text'],
            'priority': t.get('priority', 'Med'),
            'status': t.get('status', 'open'),
            'assigned_to': t.get('owner', ''),
            'context': '',
            'index': i,
        })
    return jsonify(results)


@tasks_bp.route('/api/tasks/prospect', methods=['POST'])
def api_prospect_task_create():
    """Create a new prospect task."""
    data = request.get_json(force=True)
    org = data.get('org', '').strip()
    text = data.get('text', '').strip()
    owner = data.get('assigned_to', data.get('owner', '')).strip()
    priority = data.get('priority', 'Med').strip()
    if not org or not text:
        return jsonify({'ok': False, 'error': 'org and text required'}), 400
    ok = add_prospect_task(org, text, owner, priority)
    return jsonify({'ok': ok})


@tasks_bp.route('/api/tasks/prospect/<int:task_id>/complete', methods=['POST'])
def api_prospect_task_complete(task_id):
    return jsonify({'ok': False, 'error': 'Prospect task completion by ID requires a database.'}), 501


@tasks_bp.route('/api/tasks/prospect/<int:task_id>', methods=['DELETE'])
def api_prospect_task_delete(task_id):
    return jsonify({'ok': False, 'error': 'Prospect task deletion by ID requires a database.'}), 501
