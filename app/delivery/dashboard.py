"""
Flask app — CRM dashboard (port 8000).

Local dev setup:
  echo 'DEV_USER=oscar' > app/.env
  python app/delivery/dashboard.py

Blueprint modules:
  - crm_blueprint.py  → /crm routes
"""

import os
import sys
import re

# Allow imports from app/
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Load .env from app/ directory
from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, ".env"), override=True)

from datetime import datetime
from flask import Flask, g, jsonify, request, render_template, abort, redirect, session, url_for

from delivery.crm_blueprint import crm_bp

PROJECT_ROOT = os.path.dirname(APP_DIR)
MEETINGS_DIR = os.path.join(PROJECT_ROOT, "meeting-summaries")

app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

app.register_blueprint(crm_bp)


@app.before_request
def load_user():
    """Populate g.user from session or DEV_USER env var bypass."""
    if 'user' in session:
        g.user = session['user']
    else:
        dev_user = os.environ.get('DEV_USER', '').strip()
        if dev_user:
            g.user = {'display_name': dev_user, 'email': dev_user, 'role': 'admin'}
        else:
            g.user = None


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return redirect(url_for('crm.pipeline'))


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

        if stripped.startswith('**Date:**') or stripped.startswith('**Source:**') or stripped.startswith('**Attendees:**'):
            continue

        if stripped.startswith('# '):
            _close_ul()
            continue
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


# ---------------------------------------------------------------------------
# Meeting routes
# ---------------------------------------------------------------------------

@app.route('/meetings/<path:filename>')
def meeting_detail(filename):
    if not re.match(r'^\d{4}-\d{2}-\d{2}-[\w\-]+\.md$', filename):
        abort(404)
    fp = os.path.join(MEETINGS_DIR, filename)
    if not os.path.exists(fp):
        abort(404)
    with open(fp, encoding='utf-8') as f:
        raw = f.read()

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



if __name__ == '__main__':
    port = int(os.environ.get("DASHBOARD_PORT", "8000"))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(port=port, debug=debug)
