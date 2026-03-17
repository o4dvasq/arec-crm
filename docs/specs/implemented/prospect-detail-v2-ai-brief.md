# AREC CRM — Prospect Detail Page v2: AI-Synthesized Relationship Brief

**Spec Type:** Feature enhancement (replaces raw data dump with AI synthesis)  
**Scope:** Prospect detail page — complete rework of Relationship Brief section + top card cleanup  
**Priority:** High  
**Replaces:** The previous `prospect-detail-ai-brief-fix.md` spec  

---

## Problem

The Relationship Brief section currently dumps raw data from 8 knowledge base sources directly onto the page. The result is a wall of unprocessed text: empty contact fields rendered verbatim, markdown table syntax shown as plain text, raw file contents stacked with no synthesis. A fundraiser looking at this page needs a narrative that tells them what's happening with this prospect and what to do next — not a database query result.

The data collection layer (8-source aggregation from the previous spec) is working correctly. The problem is purely presentation: raw data needs to be synthesized into intelligence.

Additionally, the top prospect card shows empty fields (Closing Round with no value) and a broken urgency display ("False" with a red emoji dot).

---

## Architecture: What Changes

```
CURRENT FLOW:
  Page load → fetch /crm/api/relationship-brief → dump raw JSON sections to HTML

NEW FLOW:
  Page load → fetch /crm/api/relationship-brief → 
    1. Check cache (localStorage, keyed by org+offering+data hash)
    2. If cache hit → render cached brief instantly
    3. If cache miss → call /crm/api/synthesize-brief (server-side Anthropic API)
    4. Render synthesized narrative in hero section
    5. Render raw reference data in collapsible sections below
```

The key architectural decision: the Anthropic API call happens **server-side** in Flask, not client-side. This keeps the API key secure and allows the prompt to be tuned without touching frontend code.

---

## 1. New Endpoint: `/crm/api/synthesize-brief`

### Request

```
POST /crm/api/synthesize-brief
Content-Type: application/json
Body: {
  "org": "Merseyside Pension Fund",
  "offering": "AREC Debt Fund II"
}
```

### Implementation

This endpoint:
1. Calls the existing relationship-brief data collection (all 8 sources)
2. Assembles the collected data into a structured prompt
3. Calls the Anthropic API (Claude Sonnet) to synthesize a narrative
4. Returns the narrative + a content hash for cache invalidation

```python
import anthropic
import hashlib
import json

# Initialize client — uses ANTHROPIC_API_KEY env var
client = anthropic.Anthropic()

@crm_bp.route('/api/synthesize-brief', methods=['POST'])
def synthesize_brief():
    data = request.get_json()
    org = data.get('org')
    offering = data.get('offering')

    if not org or not offering:
        return jsonify({"error": "org and offering required"}), 400

    # Step 1: Collect all source data (reuse existing logic)
    raw_data = collect_relationship_data(org, offering)

    # Step 2: Build content hash for cache invalidation
    content_hash = hashlib.md5(
        json.dumps(raw_data, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]

    # Step 3: Assemble the prompt context
    context_block = build_context_block(raw_data)

    # Step 4: Call Anthropic API
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=BRIEF_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Generate a relationship brief for {org} regarding {offering}.\n\n{context_block}"
                }
            ]
        )
        narrative = message.content[0].text
    except Exception as e:
        # Fallback: return raw data summary if API fails
        narrative = build_fallback_summary(raw_data)

    return jsonify({
        "narrative": narrative,
        "content_hash": content_hash,
        "raw_data": raw_data
    })
```

### `collect_relationship_data(org, offering)`

This is a refactor of the existing `/crm/api/relationship-brief` logic into a reusable function. It returns a dict with all 8 source results. Keep the existing data collection code — just extract it from the route handler into this function so both endpoints can use it.

```python
def collect_relationship_data(org, offering):
    """Collect all knowledge base data for an org/offering. 
    Returns structured dict with all 8 sources."""

    # Source 1: Prospect record
    prospect = crm_reader.get_prospect(org, offering)

    # Source 2: Organization record
    organization = crm_reader.get_organization(org)

    # Source 3: Contacts (CRM + people intel files)
    contacts = crm_reader.get_contacts_for_org(org)
    contact_names = [c.get('name', '') for c in contacts]
    people_intel = find_people_files(org, contact_names)

    # Source 4: Interaction log
    interactions = crm_reader.load_interactions(org=org)

    # Source 5: Glossary
    glossary_entry = find_glossary_entry(org)

    # Source 6: Meeting summaries
    meeting_summaries = find_meeting_summaries(org, contact_names)

    # Source 7: Active tasks
    active_tasks = find_org_tasks(org, contact_names)

    # Source 8: Email history
    email_history = get_email_history_for_org(org) if callable_exists('get_email_history_for_org') else []

    return {
        "org_name": org,
        "offering": offering,
        "prospect": prospect or {},
        "organization": organization or {},
        "contacts": contacts or [],
        "people_intel": people_intel or [],
        "glossary_entry": glossary_entry,
        "interactions": interactions[:30] if interactions else [],
        "meeting_summaries": meeting_summaries or [],
        "active_tasks": active_tasks or [],
        "email_history": email_history or []
    }
```

### `build_context_block(raw_data)`

Assembles the raw data into a text block for the AI prompt. Critical: only include non-empty data. Do not send empty fields, empty contact records, or blank sections.

```python
def build_context_block(raw_data):
    """Build structured text context for the AI synthesis prompt.
    Only includes non-empty data. No empty fields."""
    
    sections = []

    # Prospect record
    p = raw_data.get('prospect', {})
    if p:
        prospect_lines = []
        field_map = [
            ('stage', 'Stage'), ('target', 'Target'), ('committed', 'Committed'),
            ('closing', 'Closing'), ('urgent', 'Urgent'), ('assigned_to', 'Assigned To'),
            ('notes', 'Notes')
        ]
        for key, label in field_map:
            val = p.get(key)
            if val and str(val).strip() and str(val).strip().lower() not in ('false', 'none', '$0'):
                prospect_lines.append(f"- {label}: {val}")
        if prospect_lines:
            sections.append("PROSPECT RECORD:\n" + "\n".join(prospect_lines))

    # Organization
    org = raw_data.get('organization', {})
    if org:
        org_lines = []
        if org.get('type'):
            org_lines.append(f"- Type: {org['type']}")
        if org.get('notes') and org['notes'].strip():
            org_lines.append(f"- Notes: {org['notes']}")
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
            if c.get('notes') and c['notes'].strip():
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
    if glossary and glossary.strip():
        sections.append("INVESTOR BACKGROUND (GLOSSARY):\n" + glossary.strip())

    # Interactions — compact format
    interactions = raw_data.get('interactions', [])
    if interactions:
        ix_lines = []
        for ix in interactions[:20]:
            parts = [ix.get('date', ''), ix.get('type', '')]
            if ix.get('contact'):
                parts.append(ix['contact'])
            if ix.get('summary'):
                parts.append(ix['summary'])
            ix_lines.append(" — ".join(p for p in parts if p))
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
```

### `BRIEF_SYSTEM_PROMPT`

This is the core prompt that turns raw data into a fundraiser's intelligence brief. Store it as a constant in the module.

```python
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
- Today's date for staleness reference: provide the current date in the prompt.
- Do not include a title or heading. Start directly with the narrative."""
```

### `build_fallback_summary(raw_data)`

If the Anthropic API call fails, generate a minimal plain-text summary from the raw data so the page is never blank.

```python
def build_fallback_summary(raw_data):
    """Fallback summary when AI synthesis is unavailable."""
    p = raw_data.get('prospect', {})
    parts = []

    stage = p.get('stage', 'Unknown stage')
    target = p.get('target', '')
    parts.append(f"{raw_data['org_name']} is at {stage}" + (f" targeting {target}" if target else "") + ".")

    if p.get('notes'):
        parts.append(p['notes'])

    interactions = raw_data.get('interactions', [])
    if interactions:
        latest = interactions[0]
        parts.append(f"Last interaction: {latest.get('date', '')} — {latest.get('summary', '')}")

    tasks = raw_data.get('active_tasks', [])
    if tasks:
        task_text = tasks[0].replace('- [ ] ', '').strip()
        parts.append(f"Open task: {task_text}" + (f" (+{len(tasks)-1} more)" if len(tasks) > 1 else ""))

    return " ".join(parts)
```

---

## 2. Frontend: Page Layout Redesign

### New Page Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  AREC CRM    Dashboard    Pipeline    Orgs                      │
├─────────────────────────────────────────────────────────────────┤
│  <- Pipeline                                   [Edit Prospect]  │
│                                                                 │
│  Merseyside Pension Fund                                        │
│  AREC Debt Fund II                                              │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ PROSPECT CARD (compact, no empty fields)                    │ │
│ │                                                             │ │
│ │ Stage          Primary Contact       Assigned To            │ │
│ │ 6. Verbal      Susannah Friar        Oscar Vasquez          │ │
│ │                                                             │ │
│ │ Target         Last Touch            Urgent                 │ │
│ │ $50,000,000    Today (green dot)     [Yes] or hidden        │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ RELATIONSHIP BRIEF                         [Refresh]        │ │
│ │                                                             │ │
│ │ Merseyside is at Verbal, targeting $50M for the Final       │ │
│ │ close. The team met in person at their Liverpool offices    │ │
│ │ on March 2 — Tony, Oscar, and James Walton (South40) met   │ │
│ │ with Dragos, Susannah, and two Investment Committee         │ │
│ │ members: Adil Manzoor and Peter (last name TBD).           │ │
│ │ Merseyside is a previous AREC investor but was not in      │ │
│ │ Fund I. They have indicated willingness to commit...        │ │
│ │                                                             │ │
│ │ Susannah Friar is the primary contact and Investment        │ │
│ │ Manager (Property). Dragos Serbanica is on the investment   │ │
│ │ team. The @wirral.gov.uk email domain is shared across...   │ │
│ │                                                             │ │
│ │ Virtual Due Diligence calls are scheduled for March 25-26.  │ │
│ │ Oscar still needs to collect full contact details for Adil  │ │
│ │ and Peter from the IC...                                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ ACTIVE TASKS                                                │ │
│ │                                                             │ │
│ │ [ ] Prepare for DD Call on 3/25, 3/26 (Merseyside)         │ │
│ │ [ ] Get Peter's full last name from Merseyside IC           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ CONTACTS                                                    │ │
│ │                                                             │ │
│ │ Susannah Friar · Investment Manager (Property)              │ │
│ │   susannahfriar@wirral.gov.uk                               │ │
│ │ Dragos Serbanica · Investment team                          │ │
│ │   dragosserbanica@wirral.gov.uk                             │ │
│ │ Adil Manzoor · Investment Committee member                  │ │
│ │ Peter · Investment Committee member                         │ │
│ │ Zyan Nuafal                                                 │ │
│ │ Saneeza Asrar                                               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ v INTERACTION HISTORY                              3 events │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ 2026-03-02  Meeting  In-person meeting at Castle Chambers,  │ │
│ │                      Liverpool. Attendees: Tony, Oscar,     │ │
│ │                      James, Susannah, Dragos, Adil.         │ │
│ │ 2026-03-01  Email    Oscar sent Susannah summary re:        │ │
│ │                      Encore Fund III 17.25% 3-yr return     │ │
│ │ 2026-02-25  Email    Sent Credit and Index Comparisons      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ v MEETING SUMMARIES                              1 summary  │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ March 2, 2026 — Liverpool Office Visit                      │ │
│ │ Fund II pitch meeting at Merseyside Pension Fund's offices  │ │
│ │ in Liverpool, followed by dinner/drinks with the same       │ │
│ │ group...                                   [Show more]      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ > EMAIL HISTORY                                    0 emails │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Layout Decisions

1. **Relationship Brief is the hero section.** Full width, prominent, right below the prospect card. This is what the user came here to read.
2. **Active Tasks directly after the brief.** These are the "what do I need to do" items — highest actionability.
3. **Contacts section** — merged from CRM contacts + people intel files. Display only non-empty fields. Each contact is a compact line: name, title/role, email. No bullet lists, no empty fields, no raw markdown.
4. **Interaction History** — collapsible, starts expanded. Compact table-style layout: date, type badge, summary. No redundant org name on every row.
5. **Meeting Summaries** — collapsible, starts expanded. Truncated with "Show more" toggle. Parse the filename into a readable date + title for the header.
6. **Email History** — collapsible, starts collapsed (since it's currently empty and is lower priority than the other sections).

---

## 3. Top Prospect Card: Strip Empty Fields + Fix Urgency

### Empty Field Rule

Do not render any field where the value is empty, null, blank, "False", "None", or "$0". The card should only show fields that have meaningful data.

**Current fields that may be empty:**
- Closing Round → hide if blank
- Urgency → hide if not urgent (per the urgency simplification spec); show as styled indicator if urgent

### Fix Urgency Display

The current code renders urgency as a red emoji dot + the literal text "False". This is a data model bug combined with a display bug.

**Fix:**
- Read the `urgent` field from the prospect record
- If the value is truthy (`Yes`, `true`, `True`, `1`) → show a styled yellow highlight row on Pipeline, and on this card show: `URGENT` as a red CSS badge (no emoji)
- If the value is falsy (empty, `No`, `false`, `False`, `None`) → do not show the Urgency field at all
- Never display the raw string "False" or "True"

```python
# In the prospect API response, normalize urgency:
urgent_raw = prospect.get('urgent', '') or prospect.get('urgency', '')
prospect['urgent'] = str(urgent_raw).strip().lower() in ('yes', 'true', 'high', '1')
```

```javascript
// In the prospect card renderer:
if (prospect.urgent === true) {
    html += `<div class="prospect-field">
        <span class="field-label">URGENT</span>
        <span class="urgent-badge">Yes</span>
    </div>`;
}
// If not urgent, don't render anything for urgency
```

### Primary Contact Display

Currently shows all contacts semicolon-separated. Instead, show only the primary contact name on the card. Full contact list is in the Contacts section below.

```javascript
// Show only primary contact, not all contacts
const primaryContact = prospect.primary_contact || contacts[0]?.name || '';
```

---

## 4. Frontend: Synthesis + Caching Logic

### Cache Strategy

Cache the synthesized brief in localStorage, keyed by org name + offering + content hash. When the page loads:

1. Render the prospect card immediately from the existing prospect data
2. Fetch `/crm/api/relationship-brief` to get raw data + content hash
3. Check localStorage for cached brief matching this org + offering + content hash
4. If cache hit → render cached narrative immediately, render raw sections below
5. If cache miss → show brief skeleton/loading state, call `/crm/api/synthesize-brief`, cache result, render

This means the AI call only happens when the underlying data has changed. Repeat visits to the same prospect with no new data are instant.

### JavaScript Implementation

```javascript
const BRIEF_CACHE_PREFIX = 'arec_brief_';

async function loadProspectDetail(orgName, offering) {
    // Step 1: Load raw data (fast — no AI call)
    const rawResponse = await fetch(
        `/crm/api/relationship-brief?org=${enc(orgName)}&offering=${enc(offering)}`
    );
    const rawData = await rawResponse.json();
    const contentHash = rawData.content_hash;

    // Step 2: Render reference sections immediately from raw data
    renderProspectCard(rawData);
    renderActiveTasks(rawData.active_tasks);
    renderContacts(rawData);
    renderInteractionHistory(rawData.interactions);
    renderMeetingSummaries(rawData.meeting_summaries);
    renderEmailHistory(rawData.email_history);

    // Step 3: Check cache for synthesized brief
    const cacheKey = `${BRIEF_CACHE_PREFIX}${orgName}_${offering}`;
    const cached = localStorage.getItem(cacheKey);

    if (cached) {
        const cachedData = JSON.parse(cached);
        if (cachedData.content_hash === contentHash) {
            // Cache hit — render immediately
            renderNarrativeBrief(cachedData.narrative);
            return;
        }
    }

    // Step 4: Cache miss — show loading, call synthesis endpoint
    showBriefLoading();

    try {
        const synthResponse = await fetch('/crm/api/synthesize-brief', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ org: orgName, offering: offering })
        });
        const synthData = await synthResponse.json();

        // Cache the result
        localStorage.setItem(cacheKey, JSON.stringify({
            narrative: synthData.narrative,
            content_hash: synthData.content_hash,
            generated_at: new Date().toISOString()
        }));

        renderNarrativeBrief(synthData.narrative);
    } catch (err) {
        // Fallback: show raw data summary
        renderNarrativeBrief(
            'Brief generation unavailable. See reference sections below for full context.'
        );
    }
}

function renderNarrativeBrief(narrative) {
    const container = document.getElementById('relationship-brief');
    container.innerHTML = `
        <div class="brief-header">
            <h3 class="section-title">Relationship Brief</h3>
            <button class="btn-refresh" onclick="refreshBrief()" title="Regenerate brief">
                Refresh
            </button>
        </div>
        <div class="brief-narrative">${escapeHtml(narrative)}</div>
    `;
}

async function refreshBrief() {
    const cacheKey = `${BRIEF_CACHE_PREFIX}${currentOrg}_${currentOffering}`;
    localStorage.removeItem(cacheKey);
    showBriefLoading();

    const synthResponse = await fetch('/crm/api/synthesize-brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org: currentOrg, offering: currentOffering })
    });
    const synthData = await synthResponse.json();

    localStorage.setItem(cacheKey, JSON.stringify({
        narrative: synthData.narrative,
        content_hash: synthData.content_hash,
        generated_at: new Date().toISOString()
    }));

    renderNarrativeBrief(synthData.narrative);
}

function showBriefLoading() {
    document.getElementById('relationship-brief').innerHTML = `
        <div class="brief-header">
            <h3 class="section-title">Relationship Brief</h3>
        </div>
        <div class="brief-loading">
            <div class="loading-pulse"></div>
            <span>Synthesizing intelligence...</span>
        </div>
    `;
}
```

### Modify the existing `/crm/api/relationship-brief` endpoint

Add a `content_hash` field to the existing endpoint response so the frontend can use it for cache validation without making a synthesis call:

```python
@crm_bp.route('/api/relationship-brief')
def relationship_brief():
    org = request.args.get('org')
    offering = request.args.get('offering')

    raw_data = collect_relationship_data(org, offering)

    # Add content hash
    content_hash = hashlib.md5(
        json.dumps(raw_data, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]

    return jsonify({
        **raw_data,
        "content_hash": content_hash
    })
```

---

## 5. Contacts Section: Merge + Clean

The current Intelligence section dumps raw `memory/people/*.md` files verbatim, showing empty fields like `Email:`, `Phone:`, `Role:` for every contact. This must be replaced.

### New Approach: Merged Contact Cards

Merge data from two sources:
1. `crm/contacts.md` (structured CRM data)
2. `memory/people/*.md` (qualitative intel from Cowork)

For each contact, combine available fields from both sources. The people intel files contain richer context (roles, relationship dynamics, notes from structured interviews) while CRM contacts have the basics.

**Rendering rule:** For each contact, display on a single compact card:
- Name (bold)
- Title/Role (if present from either source)
- Email (if present)
- Phone (if present)
- Any notes or qualitative intel (if present, as a subtle secondary line)

**Never show:**
- Empty fields
- Raw bullet lists
- "Type: investor" (this is redundant — they're on a prospect page)
- "Organization: Merseyside Pension Fund" (redundant — we're on that org's page)

### Backend: Contact Merging

Add a helper that merges CRM contacts with people intel for display:

```python
def merge_contacts_for_display(contacts, people_intel, org_name):
    """Merge CRM contacts with people intel files.
    Returns list of dicts with only non-empty fields."""

    # Index people intel by likely contact name match
    intel_by_name = {}
    for pf in people_intel:
        content = pf.get('content', '')
        filename = pf.get('filename', '').replace('.md', '').replace('-', ' ').replace('_', ' ')
        # Try to match filename to a contact name
        for contact in contacts:
            cname = contact.get('name', '').lower()
            if cname and (cname in filename.lower() or filename.lower() in cname):
                intel_by_name[contact['name']] = content
                break
        else:
            # If no contact match, check if it's the org file
            if org_name.lower() in filename.lower():
                intel_by_name['_org_'] = content

    merged = []
    for c in contacts:
        entry = {'name': c.get('name', '')}

        # Gather non-empty fields from CRM contact
        for field in ('title', 'email', 'phone', 'role', 'notes'):
            val = c.get(field, '').strip()
            if val:
                entry[field] = val

        # Overlay/append intel from people files
        intel_content = intel_by_name.get(c.get('name', ''))
        if intel_content:
            # Parse useful fields from the intel file
            # (extract role, notes, etc. — skip redundant org/type fields)
            parsed = parse_intel_for_display(intel_content, org_name)
            for key, val in parsed.items():
                if val and key not in entry:
                    entry[key] = val

        # Only include contacts that have at least a name
        if entry.get('name'):
            merged.append(entry)

    # Add org-level intel if exists
    org_intel = intel_by_name.get('_org_')
    if org_intel:
        # This gets folded into the AI brief context, not displayed as a contact
        pass

    return merged


def parse_intel_for_display(intel_content, org_name):
    """Extract display-worthy fields from a people intel markdown file.
    Skips redundant fields like Organization and Type."""
    
    result = {}
    skip_fields = {'organization', 'type', 'fund'}
    
    for line in intel_content.split('\n'):
        line = line.strip()
        if line.startswith('- **') or line.startswith('* **'):
            # Parse "- **Field:** Value" format
            match = re.match(r'[-*]\s*\*\*(.+?):\*\*\s*(.*)', line)
            if match:
                field = match.group(1).strip().lower()
                value = match.group(2).strip()
                if field not in skip_fields and value:
                    result[field] = value
    
    return result
```

### Frontend: Contact Rendering

```javascript
function renderContacts(data) {
    const container = document.getElementById('contacts-section');
    const merged = data.merged_contacts || [];

    if (merged.length === 0) {
        container.style.display = 'none';
        return;
    }

    let html = '<h3 class="section-title">Contacts</h3>';

    for (const c of merged) {
        html += '<div class="contact-card">';
        html += `<div class="contact-name">${esc(c.name)}</div>`;

        // Title/role line
        const titleParts = [c.title, c.role].filter(Boolean);
        if (titleParts.length) {
            html += `<div class="contact-title">${esc(titleParts.join(' · '))}</div>`;
        }

        // Email
        if (c.email) {
            html += `<div class="contact-email">${esc(c.email)}</div>`;
        }

        // Phone
        if (c.phone) {
            html += `<div class="contact-phone">${esc(c.phone)}</div>`;
        }

        // Notes (qualitative intel)
        if (c.notes) {
            html += `<div class="contact-notes">${esc(c.notes)}</div>`;
        }

        html += '</div>';
    }

    container.innerHTML = html;
}
```

---

## 6. Reference Sections: Rendering Rules

### Interaction History

- Collapsible section, **starts expanded**
- Header: `INTERACTION HISTORY` with event count badge
- Compact rows: `DATE    TYPE-BADGE    SUMMARY`
- Type badges: Meeting (blue), Email (gray), Call (green), Note (purple) — CSS-only, no emojis
- If no interactions → hide section entirely

```javascript
function renderInteractionHistory(interactions) {
    const container = document.getElementById('interaction-section');
    if (!interactions || interactions.length === 0) {
        container.style.display = 'none';
        return;
    }

    const typeBadgeClass = {
        'Meeting': 'badge-meeting',
        'Email': 'badge-email',
        'Call': 'badge-call',
        'Note': 'badge-note',
        'Document Sent': 'badge-doc',
        'Document Received': 'badge-doc'
    };

    let html = `
        <div class="collapsible-header" onclick="toggleSection('interaction')">
            <h3 class="section-title">Interaction History</h3>
            <span class="section-count">${interactions.length}</span>
        </div>
        <div id="interaction-body" class="collapsible-body">`;

    for (const ix of interactions) {
        const badgeCls = typeBadgeClass[ix.type] || 'badge-default';
        html += `<div class="interaction-row">
            <span class="ix-date">${esc(ix.date || '')}</span>
            <span class="ix-type ${badgeCls}">${esc(ix.type || '')}</span>
            <span class="ix-summary">${esc(ix.summary || '')}</span>
        </div>`;
    }

    html += '</div>';
    container.innerHTML = html;
}
```

### Meeting Summaries

- Collapsible section, **starts expanded**
- Parse filename into readable header: `2026-03-02-merseyside-pension-fund-arec-south40.md` → `March 2, 2026 — Merseyside / AREC / South40`
- Show first ~300 characters of content, "Show more" expands to full
- Render markdown content as formatted HTML (bold, bullets, etc.)
- If no summaries → hide section entirely

### Active Tasks

- **Not collapsible** — always visible
- Simple checklist with checkboxes
- Checkbox click → calls task complete API (same as Tasks page)
- If no tasks → hide section entirely

### Email History

- Collapsible section, **starts collapsed**
- If empty, show collapsed header with "0" count badge, no body
- When populated, follows existing email display format

---

## 7. CSS: No Emojis Anywhere

Remove all emoji characters from the prospect detail page. Replace with CSS-only equivalents.

```css
/* Section headers — plain text, left accent border */
.section-title {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #94a3b8;
    border-left: 3px solid #3b82f6;
    padding-left: 8px;
    margin: 0;
}

/* Urgency badge — CSS only */
.urgent-badge {
    display: inline-block;
    background: #ef4444;
    color: white;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    text-transform: uppercase;
}

/* Staleness dots — CSS only */
.staleness-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-left: 6px;
    vertical-align: middle;
}
.staleness-fresh { background: #22c55e; }   /* < 7 days */
.staleness-stale { background: #f59e0b; }   /* 8-14 days */
.staleness-cold { background: #ef4444; }     /* 15+ days */

/* Interaction type badges — CSS only */
.ix-type {
    display: inline-block;
    font-size: 11px;
    font-weight: 500;
    padding: 1px 6px;
    border-radius: 3px;
    min-width: 55px;
    text-align: center;
}
.badge-meeting { background: #1e3a5f; color: #93c5fd; }
.badge-email { background: #374151; color: #d1d5db; }
.badge-call { background: #14532d; color: #86efac; }
.badge-note { background: #3b0764; color: #d8b4fe; }
.badge-doc { background: #422006; color: #fcd34d; }

/* Section count badge */
.section-count {
    display: inline-block;
    background: #374151;
    color: #9ca3af;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 10px;
    margin-left: 8px;
}

/* Brief narrative */
.brief-narrative {
    color: #e2e8f0;
    line-height: 1.65;
    font-size: 14px;
    padding: 16px 0;
    white-space: pre-wrap;
}

/* Loading pulse animation */
.brief-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #94a3b8;
    padding: 20px 0;
    font-size: 13px;
}
.loading-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #3b82f6;
    animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
}

/* Refresh button */
.btn-refresh {
    background: none;
    border: 1px solid #475569;
    color: #94a3b8;
    font-size: 12px;
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
}
.btn-refresh:hover {
    border-color: #3b82f6;
    color: #3b82f6;
}

/* Contact cards */
.contact-card {
    padding: 8px 0;
    border-bottom: 1px solid #1e293b;
}
.contact-card:last-child { border-bottom: none; }
.contact-name { font-weight: 600; color: #e2e8f0; }
.contact-title { font-size: 13px; color: #94a3b8; }
.contact-email { font-size: 13px; color: #60a5fa; }
.contact-phone { font-size: 13px; color: #94a3b8; }
.contact-notes { font-size: 13px; color: #94a3b8; font-style: italic; margin-top: 2px; }

/* Collapsible sections */
.collapsible-header {
    display: flex;
    align-items: center;
    cursor: pointer;
    padding: 12px 0;
}
.collapsible-body {
    overflow: hidden;
    transition: max-height 0.3s ease;
}
.collapsible-body.collapsed {
    max-height: 0;
}

/* Interaction rows */
.interaction-row {
    display: grid;
    grid-template-columns: 90px 70px 1fr;
    gap: 8px;
    padding: 6px 0;
    border-bottom: 1px solid #1e293b;
    font-size: 13px;
}
.ix-date { color: #94a3b8; font-variant-numeric: tabular-nums; }
.ix-summary { color: #cbd5e1; }
```

---

## 8. Environment Setup

The synthesis endpoint requires the Anthropic Python SDK and an API key.

### Install dependency

```
pip install anthropic --break-system-packages
```

### API Key

The endpoint reads `ANTHROPIC_API_KEY` from the environment. Add it to whatever launch mechanism runs the Flask app (launchd plist, shell script, .env file).

Check how the app is currently launched. If it uses a `.env` file or launchd plist, add:

```
ANTHROPIC_API_KEY=sk-ant-...
```

If the app does not have an existing env var loading mechanism, add `python-dotenv` and a `.env` file:

```
pip install python-dotenv --break-system-packages
```

Then at the top of `dashboard.py` (or wherever the Flask app is created):

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## 9. Discovery Step (Do First)

Before implementing, inspect the codebase:

1. **Find the current relationship-brief endpoint** — confirm it already collects data from all 8 sources per the previous spec. If it does, refactor the data collection into `collect_relationship_data()`. If it doesn't, implement the full 8-source collection first.
2. **Find the prospect detail template** — identify the exact HTML file and the blocks for the prospect card, relationship brief, and reference sections.
3. **Find the prospect card rendering** — identify the urgency display bug (emoji + "False") and the empty field rendering.
4. **Check for existing Anthropic SDK usage** — the app may already import `anthropic` for other features. Reuse existing patterns.
5. **Check the launch mechanism** — how is `ANTHROPIC_API_KEY` set? .env file? launchd? export in shell script?
6. **Verify file paths** — confirm `memory/people/`, `glossary.md`, `TASKS.md`, `memory/` paths against the app's `BASE_DIR` or equivalent constant.
7. **Emoji audit** — run: `grep -rPn '[\x{1F000}-\x{1FFFF}\x{2600}-\x{27BF}]' templates/ static/crm/` to find all emoji usage on this page.

---

## 10. File Changes Summary

| File | Action |
|------|--------|
| `sources/relationship_brief.py` | **NEW or MODIFY** — Add `collect_relationship_data()`, `build_context_block()`, `BRIEF_SYSTEM_PROMPT`, `build_fallback_summary()`, `merge_contacts_for_display()`, `parse_intel_for_display()` |
| `delivery/dashboard.py` (CRM blueprint) | **MODIFY** — Add `POST /crm/api/synthesize-brief` endpoint. Refactor existing `/crm/api/relationship-brief` to use `collect_relationship_data()` + add `content_hash`. Import anthropic SDK. |
| Prospect detail template (HTML) | **MODIFY** — Restructure page layout per Section 2. Remove all emojis. Update prospect card to hide empty fields. |
| `static/crm/crm.js` | **MODIFY** — Add caching logic, `loadProspectDetail()`, `refreshBrief()`, contact merging renderer, collapsible section logic. Remove emoji literals. |
| `static/crm/crm.css` | **MODIFY** — Add all styles from Section 7. Remove emoji-dependent styles. |
| `.env` or launch config | **MODIFY** — Add `ANTHROPIC_API_KEY` |

---

## 11. Acceptance Criteria

1. Page loads prospect card immediately with no empty fields — any field with no value is hidden
2. Urgency shows CSS badge ("URGENT") when true, is hidden entirely when false — no emojis, no "False" text
3. Primary Contact on card shows only the primary contact name, not all contacts semicolon-separated
4. Relationship Brief section shows AI-synthesized narrative paragraph(s) — written in direct professional prose, no bullets, no headers
5. Brief loads from localStorage cache when content hash matches (instant on repeat visits)
6. Brief regenerates via Refresh button (clears cache, calls synthesis endpoint)
7. If synthesis API fails, fallback summary renders from raw data — page is never blank
8. Active Tasks section shows open tasks with working checkboxes
9. Contacts section shows merged CRM + people intel data with only non-empty fields
10. Interaction History shows compact rows with CSS type badges, collapsible, starts expanded
11. Meeting Summaries render with readable date headers, truncated with "Show more", collapsible
12. Email History section is collapsible, starts collapsed
13. Empty sections are hidden entirely — no "No data found" messages except the brief fallback
14. Zero emoji characters anywhere on the page (verified by grep)
15. No regressions to Pipeline page, Org page, or other CRM routes
16. Anthropic API key loaded from environment, not hardcoded
