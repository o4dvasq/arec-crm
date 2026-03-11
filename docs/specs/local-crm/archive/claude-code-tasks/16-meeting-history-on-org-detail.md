# Task 16 — Add Meeting History to Org Detail Page

## Enhancement
Display a Meeting History section on the Org Detail page. Each meeting entry is sourced from:
1. Oscar's Outlook calendar (matched by org name or contact names in attendees)
2. Notion meeting transcripts (matched by title or attendees)

Meeting entries should be persisted and auto-populated when identified.

## Files to Modify
- `app/templates/crm_org_detail.html` (new UI section)
- `app/delivery/dashboard.py` (new API endpoints)
- `app/sources/crm_reader.py` (new meeting history storage)
- `crm/meeting_history.md` (new data file)

## Data Model

### New file: `crm/meeting_history.md`

```markdown
# Meeting History

## Hillwood
- **2026-03-01** | Strategy Call | Oscar, Tony, Ross Perot Jr. | [Notion](https://notion.so/...)
- **2026-02-15** | Due Diligence Review | Oscar, Zach | calendar

## Northern Trust
- **2026-02-28** | Fund II Presentation | Oscar, Jim Hartman, Lewis | [Notion](https://notion.so/...)
```

Format per entry:
```
- **YYYY-MM-DD** | Title | Attendees | Source
```

Where Source is either:
- `calendar` — matched from Outlook
- `[Notion](url)` — linked to Notion meeting notes
- `calendar + [Notion](url)` — both sources matched

### crm_reader.py — Parse/write meeting history

```python
MEETING_HISTORY_PATH = os.path.join(CRM_DIR, 'meeting_history.md')

def load_meeting_history(org: str) -> list[dict]:
    """Return list of {date, title, attendees, source, notion_url} for an org."""
    # Parse meeting_history.md, find ## Org section, return entries

def add_meeting_entry(org: str, date: str, title: str, attendees: str, source: str, notion_url: str = '') -> None:
    """Append a meeting entry under the org's section. Create section if needed."""
    # Deduplicate by date + title to avoid duplicates on re-scan
```

### dashboard.py — API endpoints

```python
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
```

### crm_org_detail.html — Meeting History section

Add a new card between the Contacts and Prospects sections:

```html
<!-- Section 2.5: Meeting History -->
<div class="card">
  <div class="card-header">
    <span class="card-title">Meeting History</span>
    <button class="btn btn-primary btn-sm" onclick="openAddMeetingForm()">+ Add Meeting</button>
  </div>
  <div class="card-body">
    <div id="meeting-list"></div>
    <div id="add-meeting-form" style="display:none">
      <!-- Inline form for manual entry -->
      <div class="form-grid">
        <div class="form-group">
          <label>Date</label>
          <input type="date" id="mtg-date">
        </div>
        <div class="form-group">
          <label>Title</label>
          <input type="text" id="mtg-title" placeholder="Meeting title">
        </div>
        <div class="form-group">
          <label>Attendees</label>
          <input type="text" id="mtg-attendees" placeholder="Oscar, Tony, ...">
        </div>
      </div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <button class="btn btn-primary btn-sm" onclick="submitMeeting()">Add</button>
        <button class="btn btn-ghost btn-sm" onclick="closeAddMeetingForm()">Cancel</button>
      </div>
    </div>
  </div>
</div>
```

### crm_org_detail.html — JavaScript

```javascript
let meetings = [];

async function loadMeetings() {
  const resp = await fetch(`/crm/api/org/${encodeURIComponent(ORG_NAME)}/meetings`);
  meetings = await resp.json();
  renderMeetings();
}

function renderMeetings() {
  const list = document.getElementById('meeting-list');
  if (!meetings.length) {
    list.innerHTML = '<p class="muted">No meetings recorded yet.</p>';
    return;
  }
  // Sort by date descending
  meetings.sort((a, b) => b.date.localeCompare(a.date));
  list.innerHTML = meetings.map(m => `
    <div style="display:flex; gap:12px; padding:8px 0; border-bottom:1px solid #f1f5f9; font-size:13px;">
      <span style="color:#64748b; min-width:85px;">${escHtml(m.date)}</span>
      <span style="font-weight:500; color:#1e293b; flex:1;">${escHtml(m.title)}</span>
      <span style="color:#94a3b8;">${escHtml(m.attendees)}</span>
      ${m.notion_url ? `<a href="${escHtml(m.notion_url)}" target="_blank" style="color:#2563eb; font-size:12px;">Notion</a>` : ''}
    </div>
  `).join('');
}

function openAddMeetingForm() {
  document.getElementById('add-meeting-form').style.display = 'block';
  document.getElementById('mtg-date').value = new Date().toISOString().slice(0, 10);
  document.getElementById('mtg-title').focus();
}
function closeAddMeetingForm() {
  document.getElementById('add-meeting-form').style.display = 'none';
}

async function submitMeeting() {
  const date = document.getElementById('mtg-date').value;
  const title = document.getElementById('mtg-title').value.trim();
  const attendees = document.getElementById('mtg-attendees').value.trim();
  if (!date || !title) return;
  const resp = await fetch(`/crm/api/org/${encodeURIComponent(ORG_NAME)}/meetings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date, title, attendees, source: 'manual' }),
  });
  if (resp.ok) {
    closeAddMeetingForm();
    loadMeetings();
  }
}
```

Call `loadMeetings()` from `init()`.

## Auto-Population Strategy (for productivity:update skill)

During the daily `/productivity:update` run:
1. Pull Notion meeting notes for the past 7 days
2. For each meeting, check attendee names and title against known org names + contacts
3. If matched, call `POST /crm/api/org/{org}/meetings` with the Notion URL
4. Pull Outlook calendar events
5. Match attendee emails/names against contacts_index.md
6. If matched, add calendar entry

This auto-population logic lives in the productivity skill, not in the Flask app. The Flask app just provides the CRUD API.

## Testing
1. Open Org Detail for any org
2. Meeting History section should appear (empty initially)
3. Click "+ Add Meeting" → fill in date, title, attendees → Add
4. Entry appears in the list sorted by date descending
5. Verify entry is written to `crm/meeting_history.md`
6. If a Notion URL is present, it should render as a clickable link
