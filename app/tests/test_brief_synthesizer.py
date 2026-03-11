"""
test_brief_synthesizer.py — Tests for briefing/brief_synthesizer.py.

All Claude API calls are mocked — no live API requests made.
"""

import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from briefing.brief_synthesizer import call_claude_brief


def _mock_client(response_text: str):
    """Build a mock anthropic.Anthropic() that returns response_text."""
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client = MagicMock()
    client.messages.create.return_value = msg
    return client


# ---------------------------------------------------------------------------
# want_json=False — plain text response
# ---------------------------------------------------------------------------

def test_plain_text_returns_raw():
    raw = "This is a plain narrative brief."
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=_mock_client(raw)):
        narrative, glance = call_claude_brief("system", "user", want_json=False)
    assert narrative == raw
    assert glance == ''


# ---------------------------------------------------------------------------
# want_json=True — valid JSON
# ---------------------------------------------------------------------------

def test_valid_json_parsed():
    payload = {'narrative': 'Full narrative.', 'at_a_glance': 'Follow-up scheduled'}
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=_mock_client(json.dumps(payload))):
        narrative, glance = call_claude_brief("system", "user", want_json=True)
    assert narrative == 'Full narrative.'
    assert glance == 'Follow-up scheduled'


def test_markdown_fenced_json_parsed():
    payload = {'narrative': 'Fenced narrative.', 'at_a_glance': 'Status ok'}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=_mock_client(fenced)):
        narrative, glance = call_claude_brief("system", "user", want_json=True)
    assert narrative == 'Fenced narrative.'
    assert glance == 'Status ok'


def test_plain_fenced_json_parsed():
    payload = {'narrative': 'Plain fence.', 'at_a_glance': 'Done'}
    fenced = f"```\n{json.dumps(payload)}\n```"
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=_mock_client(fenced)):
        narrative, glance = call_claude_brief("system", "user", want_json=True)
    assert narrative == 'Plain fence.'
    assert glance == 'Done'


# ---------------------------------------------------------------------------
# want_json=True — malformed or partial JSON
# ---------------------------------------------------------------------------

def test_malformed_json_returns_raw():
    bad = "not json at all { oops"
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=_mock_client(bad)):
        narrative, glance = call_claude_brief("system", "user", want_json=True)
    assert narrative == bad
    assert glance == ''


def test_missing_at_a_glance_defaults_empty():
    payload = {'narrative': 'Narrative only.'}
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=_mock_client(json.dumps(payload))):
        narrative, glance = call_claude_brief("system", "user", want_json=True)
    assert narrative == 'Narrative only.'
    assert glance == ''


def test_missing_narrative_falls_back_to_raw():
    payload = {'at_a_glance': 'Status only'}
    raw = json.dumps(payload)
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=_mock_client(raw)):
        narrative, glance = call_claude_brief("system", "user", want_json=True)
    # narrative falls back to raw when 'narrative' key absent
    assert narrative == raw
    assert glance == 'Status only'


def test_empty_at_a_glance_stripped_to_empty():
    payload = {'narrative': 'Narrative.', 'at_a_glance': '   '}
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=_mock_client(json.dumps(payload))):
        narrative, glance = call_claude_brief("system", "user", want_json=True)
    assert glance == ''


# ---------------------------------------------------------------------------
# JSON suffix injected only when want_json=True
# ---------------------------------------------------------------------------

def test_json_suffix_injected_when_want_json():
    """AT_A_GLANCE_JSON_SUFFIX must appear in the system prompt sent to Claude."""
    payload = {'narrative': 'x', 'at_a_glance': 'y'}
    client = _mock_client(json.dumps(payload))
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=client):
        call_claude_brief("base_system", "user", want_json=True)
    called_system = client.messages.create.call_args[1]['system']
    assert 'base_system' in called_system
    assert 'JSON' in called_system  # suffix includes "JSON"


def test_json_suffix_not_injected_when_plain():
    """System prompt must be passed unchanged when want_json=False."""
    raw = "response"
    client = _mock_client(raw)
    with patch('briefing.brief_synthesizer.anthropic.Anthropic', return_value=client):
        call_claude_brief("plain_system", "user", want_json=False)
    called_system = client.messages.create.call_args[1]['system']
    assert called_system == 'plain_system'
