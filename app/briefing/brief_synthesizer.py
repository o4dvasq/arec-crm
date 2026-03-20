"""
brief_synthesizer.py — Shared Claude API call + JSON parsing for all brief types.

Consolidates the duplicated synthesis pattern from dashboard.py:
- _synthesize_and_persist_brief()
- api_synthesize_brief()
- api_synthesize_org_brief()
"""

import re
import json

import anthropic

AT_A_GLANCE_JSON_SUFFIX = (
    "\n\nIMPORTANT: Respond with ONLY a valid JSON object — no preamble, "
    "no markdown fences — in this exact format:\n"
    '{"narrative": "<2-4 paragraph prose brief>", '
    '"at_a_glance": "<2 sentences max, ~150 chars: condensed version of the narrative brief — where the relationship stands and what\'s next>"}\n\n'
    "at_a_glance examples:\n"
    '- "Met March 15 to review terms; Viktor sending revised LOI by March 24. $25M target, strong alignment on fund thesis."\n'
    '- "Waiting on response to our March 3 email; Paige to follow up by end of week. Relationship warm but no commitment yet."\n'
    '- "Gone unresponsive since February IC meeting; Oscar to call directly before March 31. $10M soft circle at risk."\n'
    '- "Verbal $15M commit after March 10 IC approval. Legal reviewing sub docs, targeting April close."\n'
    '- "Intro call with portfolio team scheduled March 28 via Paige. No prior relationship — first real touchpoint."\n'
    "Use specific dates and names. 150 characters MAX, 2 sentences MAX."
)

TASK_EXTRACTION_SYSTEM_PROMPT = """You extract actionable tasks from CRM prospect notes for a real estate private equity fundraising team.

RULES:
1. Only extract CLEAR action items — things someone needs to DO. Ignore status updates, historical notes, and general observations.
2. Each task must have a specific, concrete action verb (send, follow up, schedule, call, prepare, review, etc.).
3. For assignee: match any first name or full name mentioned to the team roster provided. If no name is mentioned for a task, leave assignee as empty string "".
4. For priority: use "Hi" if the task has a deadline or time pressure word (before, by, urgent, ASAP, this week). Use "Med" for everything else.
5. For source_snippet: quote the specific phrase from the notes that this task was extracted from. Keep it under 80 characters.
6. If the notes contain NO actionable tasks, return an empty JSON array: []
7. Do NOT invent tasks. Do NOT infer tasks that are not stated or clearly implied in the notes.
8. Maximum 5 tasks per extraction. If more exist, pick the most important or most recent.

RESPOND WITH ONLY a JSON array. No preamble, no explanation, no markdown fencing.

Example output:
[
  {
    "text": "Send updated track record to allocation committee",
    "assignee": "Oscar Vasquez",
    "priority": "Hi",
    "source_snippet": "Oscar needs to send updated track record before March meeting"
  }
]"""


def call_claude_brief(
    system_prompt: str,
    user_content: str,
    max_tokens: int = 1600,
    want_json: bool = False,
) -> tuple[str, str]:
    """
    Call Claude API for a brief. Returns (narrative, at_a_glance).

    If want_json=True, appends the JSON format instruction to the system prompt
    and parses the response. On JSON parse failure, returns the raw response as
    narrative with an empty at_a_glance.

    If want_json=False, returns (full text response, '').

    Raises any Claude API exceptions to the caller so callers can apply their
    own fallback logic.
    """
    actual_system = system_prompt + AT_A_GLANCE_JSON_SUFFIX if want_json else system_prompt

    client = anthropic.Anthropic()
    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=max_tokens,
        system=actual_system,
        messages=[{'role': 'user', 'content': user_content}],
    )
    raw = message.content[0].text

    if not want_json:
        return raw, ''

    # Extract JSON object — handles preamble text and/or markdown fences
    clean = raw.strip()
    start = clean.find('{')
    end = clean.rfind('}')
    if start != -1 and end != -1 and end > start:
        clean = clean[start:end + 1]
    try:
        parsed = json.loads(clean)
        narrative = parsed.get('narrative', raw)
        at_a_glance = (parsed.get('at_a_glance', '') or '').strip()
        return narrative, at_a_glance
    except (json.JSONDecodeError, AttributeError):
        return raw, ''


def extract_tasks_from_notes(
    org_name: str,
    offering_name: str,
    notes_text: str,
    team_roster: list[str]
) -> list[dict]:
    """
    Extract suggested tasks from a prospect's Notes field.

    Args:
        org_name: Prospect org name (for task context suffix)
        offering_name: Offering name (for context)
        notes_text: The raw Notes field string from the prospect record
        team_roster: List of team member full names from config.md

    Returns:
        List of dicts: [{text, assignee, priority, source_snippet}, ...]
        Returns empty list if notes_text is empty or no tasks found.
    """
    if not notes_text or not notes_text.strip():
        return []

    team_names_str = ", ".join(team_roster)

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=TASK_EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Prospect: {org_name} ({offering_name})\n"
                        f"Team members: {team_names_str}\n\n"
                        f"Notes:\n{notes_text}"
                    )
                }
            ]
        )
        raw = message.content[0].text

        # Parse JSON — handle markdown fencing if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]

        tasks = json.loads(cleaned)

        # Validate structure
        validated = []
        for t in tasks:
            if isinstance(t, dict) and "text" in t:
                validated.append({
                    "text": str(t.get("text", "")),
                    "assignee": str(t.get("assignee", "")),
                    "priority": str(t.get("priority", "Med")),
                    "source_snippet": str(t.get("source_snippet", ""))
                })
        return validated

    except Exception as e:
        print(f"Task extraction failed for {org_name}: {e}")
        return []
