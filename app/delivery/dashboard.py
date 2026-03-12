"""
Flask app — productivity dashboard (port 3001).

Blueprint modules:
  - crm_blueprint.py  → /crm routes
  - tasks_blueprint.py → /tasks routes
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

# Load .env from app/ directory
from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, ".env"))

from datetime import date, datetime, timezone, timedelta
from flask import Flask, jsonify, request, render_template, abort

from sources.crm_reader import load_crm_config
from delivery.crm_blueprint import crm_bp
from delivery.tasks_blueprint import tasks_bp, _parse_task_line
import db

PROJECT_ROOT = os.path.dirname(APP_DIR)
TASKS_PATH = os.path.join(PROJECT_ROOT, "TASKS.md")
MEETINGS_DIR = os.path.join(PROJECT_ROOT, "meeting-summaries")
CALENDAR_PATH = os.path.join(PROJECT_ROOT, "dashboard_calendar.json")

app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)

app.register_blueprint(crm_bp)
app.register_blueprint(tasks_bp)

# Initialize database (PostgreSQL backend)
db.init_app(app)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route('/')
def dashboard():
    all_sections = _load_tasks_grouped()
    # Dashboard shows all sections (except Done) split across two columns
    tasks_by_section = [s for s in all_sections if s['name'] != 'Done']
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
                parsed = _parse_task_line(line, current['name'])
                parsed['done'] = parsed['complete']
                parsed['index'] = len(current['tasks'])
                current['tasks'].append(parsed)
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


def _render_meeting_markdown(text: str) -> str:
    """Convert meeting summary markdown to safe HTML for display."""
    import html as html_mod
    lines = text.splitlines()
    out = []
    in_ul = False

    def _inline(s):
        s = html_mod.escape(s)
        s = re.sub(r'\*\*([^*\n]+)\*\*', r'<strong>\1</strong>', s)
        s = re.sub(r'\*([^*\n]+)\*', r'<em>\1</em>', s)
        s = re.sub(r'~~([^~\n]+)~~', r'<del>\1</del>', s)
        s = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)',
                   r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
        return s

    def _close_ul():
        nonlocal in_ul
        if in_ul:
            out.append('</ul>')
            in_ul = False

    for line in lines:
        stripped = line.strip()

        # Skip raw header metadata lines (rendered in page header already)
        if stripped.startswith('**Date:**') or stripped.startswith('**Source:**') or stripped.startswith('**Attendees:**'):
            continue

        if stripped.startswith('# '):
            _close_ul()
            continue  # Title already shown in header
        elif stripped.startswith('## '):
            _close_ul()
            out.append(f'<h2>{html_mod.escape(stripped[3:])}</h2>')
        elif stripped.startswith('### '):
            _close_ul()
            out.append(f'<h3>{html_mod.escape(stripped[4:])}</h3>')
        elif stripped.startswith('- [x] ') or stripped.startswith('- [X] '):
            if not in_ul:
                out.append('<ul>'); in_ul = True
            out.append(f'<li class="checked">{_inline(stripped[6:])}</li>')
        elif stripped.startswith('- [ ] '):
            if not in_ul:
                out.append('<ul>'); in_ul = True
            out.append(f'<li>{_inline(stripped[6:])}</li>')
        elif stripped.startswith('- '):
            if not in_ul:
                out.append('<ul>'); in_ul = True
            out.append(f'<li>{_inline(stripped[2:])}</li>')
        elif re.match(r'^-{3,}$', stripped):
            _close_ul()
            out.append('<hr>')
        elif stripped == '':
            _close_ul()
        else:
            _close_ul()
            out.append(f'<p>{_inline(stripped)}</p>')

    _close_ul()
    return '\n'.join(out)


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


# ---------------------------------------------------------------------------
# Meeting routes
# ---------------------------------------------------------------------------

@app.route('/meetings/<path:filename>')
def meeting_detail(filename):
    """Show and optionally edit a meeting summary markdown file."""
    # Security: only allow filenames that look like YYYY-MM-DD-*.md
    if not re.match(r'^\d{4}-\d{2}-\d{2}-[\w\-]+\.md$', filename):
        abort(404)
    fp = os.path.join(MEETINGS_DIR, filename)
    if not os.path.exists(fp):
        abort(404)
    with open(fp, encoding='utf-8') as f:
        raw = f.read()

    # Parse header fields for the template
    meeting_date = ''
    source_url = ''
    source_label = ''
    attendees = ''
    title = ''

    for line in raw.splitlines():
        if line.startswith('# ') and not title:
            title = line[2:].strip()
        elif line.startswith('**Date:**'):
            meeting_date = line.split(':', 1)[1].strip()
        elif line.startswith('**Attendees:**'):
            attendees = line.split(':', 1)[1].strip()
        elif line.startswith('**Source:**'):
            um = re.search(r'\[([^\]]+)\]\((https?://[^\)]+)\)', line)
            if um:
                source_label = um.group(1)
                source_url = um.group(2)

    rendered_html = _render_meeting_markdown(raw)
    return render_template(
        'meeting_detail.html',
        filename=filename,
        title=title or filename,
        meeting_date=meeting_date,
        attendees=attendees,
        source_url=source_url,
        source_label=source_label,
        raw_content=raw,
        rendered_html=rendered_html,
    )


@app.route('/meetings/<path:filename>/save', methods=['POST'])
def meeting_save(filename):
    """Save updated meeting content."""
    if not re.match(r'^\d{4}-\d{2}-\d{2}-[\w\-]+\.md$', filename):
        abort(404)
    fp = os.path.join(MEETINGS_DIR, filename)
    if not os.path.exists(fp):
        abort(404)
    data = request.get_json(force=True)
    content = data.get('content', '')
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Calendar API
# ---------------------------------------------------------------------------

@app.route('/api/calendar/refresh', methods=['POST'])
def api_calendar_refresh():
    """Fetch today's calendar events from Microsoft Graph and update dashboard_calendar.json."""
    try:
        from auth.graph_auth import get_access_token, _load_cache, _build_app, SCOPES
        from sources.ms_graph import get_today_events, get_tomorrow_events
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'}), 500

    # Check if we have a valid cached token first (non-blocking)
    try:
        cache = _load_cache()
        app_msal = _build_app(cache)
        accounts = app_msal.get_accounts()

        if not accounts:
            return jsonify({
                'ok': False,
                'error': 'Not authenticated. Run `/productivity:update` from command line to authenticate with Microsoft Graph.',
                'needsAuth': True
            }), 401

        # Try silent token acquisition
        result = app_msal.acquire_token_silent(SCOPES, account=accounts[0])
        if not result or "access_token" not in result:
            return jsonify({
                'ok': False,
                'error': 'Token expired. Run `/productivity:update` from command line to re-authenticate.',
                'needsAuth': True
            }), 401

        token = result["access_token"]
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Auth check failed: {e}'}), 500

    try:
        raw_events = get_today_events(token)
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Graph API error: {e}'}), 500

    # After 3 PM Pacific, also fetch tomorrow's events
    raw_tomorrow = []
    try:
        from zoneinfo import ZoneInfo
        pacific = ZoneInfo("America/Los_Angeles")
        now_pacific = datetime.now(pacific)
        if now_pacific.hour >= 15:
            try:
                raw_tomorrow = get_tomorrow_events(token)
            except Exception:
                raw_tomorrow = []
    except Exception:
        pacific = None

    # Convert Graph events to dashboard format
    def _parse_dt(s, tz_fallback):
        if not s:
            return None
        s = s.rstrip('Z')
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        if dt.tzinfo is None:
            try:
                from zoneinfo import ZoneInfo as ZI
                dt = dt.replace(tzinfo=ZI(tz_fallback))
            except Exception:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _fmt_time(dt):
        if not dt:
            return ''
        h = dt.hour % 12 or 12
        ampm = 'AM' if dt.hour < 12 else 'PM'
        return f"{h}:{dt.minute:02d} {ampm}"

    def _format_events(events_list, day_label):
        result = []
        for evt in events_list:
            if evt.get('is_all_day'):
                continue
            start_raw = evt.get('start', '')
            end_raw = evt.get('end', '')
            tz_name = evt.get('timezone', 'UTC')
            start_dt = _parse_dt(start_raw, tz_name)
            end_dt = _parse_dt(end_raw, tz_name)
            if start_dt and pacific:
                start_dt = start_dt.astimezone(pacific)
            if end_dt and pacific:
                end_dt = end_dt.astimezone(pacific)
            time_str = f"{_fmt_time(start_dt)} – {_fmt_time(end_dt)}" if start_dt and end_dt else ''
            attendees = ', '.join(
                a['name'] or a['email']
                for a in evt.get('attendees', [])
                if a.get('name') or a.get('email')
            )
            end_time_iso = end_dt.isoformat() if end_dt else ''
            title = evt.get('subject', '')
            title = re.sub(r'\s*\((Past|Future)\)\s*$', '', title).strip()
            result.append({
                'time': time_str,
                'title': title,
                'attendees': attendees,
                'location': evt.get('location', ''),
                'end_time': end_time_iso,
                'day': day_label,
            })
        return result

    formatted = _format_events(raw_events, 'today')
    if raw_tomorrow:
        formatted += _format_events(raw_tomorrow, 'tomorrow')

    try:
        with open(CALENDAR_PATH, 'w', encoding='utf-8') as f:
            json.dump(formatted, f, ensure_ascii=False)
    except IOError as e:
        return jsonify({'ok': False, 'error': f'Could not write calendar: {e}'}), 500

    return jsonify({'ok': True, 'events': formatted, 'count': len(formatted)})


# ---------------------------------------------------------------------------
# Legacy dashboard task routes (simple text-replacement API)
# ---------------------------------------------------------------------------

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


@app.route('/api/task/status', methods=['PATCH'])
def task_status_update():
    from sources.memory_reader import update_task_status
    data = request.get_json(force=True)
    section = data.get('section', '').strip()
    task_text = data.get('task_text', '').strip()
    new_status = data.get('new_status', '').strip()

    if not section or not task_text or not new_status:
        return jsonify({'success': False, 'error': 'section, task_text, and new_status are required'}), 400

    if new_status not in ['New', 'In Progress', 'Complete']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    success = update_task_status(section, task_text, new_status)

    if success:
        return jsonify({'success': True, 'new_status': new_status})
    else:
        return jsonify({'success': False, 'error': 'Task not found'}), 404


if __name__ == '__main__':
    port = int(os.environ.get("DASHBOARD_PORT", "3001"))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(port=port, debug=debug)
