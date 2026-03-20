"""
test_task_parsing.py — Tests for task line parsing logic.
"""

import os
import sys
import pytest

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from sources.memory_reader import _parse_task_line as parse_task_line


# ---------------------------------------------------------------------------
# Priority extraction
# ---------------------------------------------------------------------------

def test_priority_hi():
    t = parse_task_line('- [ ] **[Hi]** Send deck to UTIMCO')
    assert t['priority'] == 'Hi'
    assert t['text'] == 'Send deck to UTIMCO'
    assert t['status'] == 'New'


def test_priority_med():
    t = parse_task_line('- [ ] **[Med]** Review LP agreement')
    assert t['priority'] == 'Med'


def test_priority_low():
    t = parse_task_line('- [ ] **[Low]** Update website bio')
    assert t['priority'] == 'Low'


def test_priority_missing_defaults_to_med():
    t = parse_task_line('- [ ] No priority tag here')
    assert t['priority'] == 'Med'


# ---------------------------------------------------------------------------
# Status extraction
# ---------------------------------------------------------------------------

def test_status_new():
    t = parse_task_line('- [ ] **[Hi]** Call Jared')
    assert t['status'] == 'New'
    assert t['complete'] is False


def test_status_in_progress():
    t = parse_task_line('- [ ] **[Hi]** **[→]** Call Jared')
    assert t['status'] == 'In Progress'
    assert t['text'] == 'Call Jared'
    assert t['complete'] is False


def test_status_complete():
    t = parse_task_line('- [x] **[Hi]** Call Jared')
    assert t['status'] == 'Complete'
    assert t['complete'] is True


def test_legacy_status_tag_stripped():
    t = parse_task_line('- [ ] **[Med]** Review docs [STATUS:InProgress] extra')
    assert '[STATUS:' not in t['text']


# ---------------------------------------------------------------------------
# Org suffix extraction
# ---------------------------------------------------------------------------

def test_org_suffix_extracted():
    t = parse_task_line('- [ ] **[Hi]** Follow up with Jared (UTIMCO)')
    assert t['org'] == 'UTIMCO'
    assert 'UTIMCO' not in t['text']
    assert t['text'] == 'Follow up with Jared'


def test_dollar_suffix_not_treated_as_org():
    t = parse_task_line('- [ ] **[Med]** Raise capital ($50M target)')
    assert t['org'] == ''
    assert '$50M target' in t['text']


def test_numeric_suffix_not_treated_as_org():
    t = parse_task_line('- [ ] **[Low]** Meet at 3pm (10 mins)')
    assert t['org'] == ''


# ---------------------------------------------------------------------------
# Assigned-to extraction
# ---------------------------------------------------------------------------

def test_assigned_to_inline():
    t = parse_task_line('- [ ] **[Hi]** Draft NDA — assigned:Paige')
    assert t['assigned_to'] == 'Paige'
    assert 'assigned:' not in t['text']


def test_assigned_to_legacy_at_tag():
    t = parse_task_line('- [ ] **[Med]** **@Paige** Review LP docs')
    assert t['assigned_to'] == 'Paige'
    assert '@Paige' not in t['text']


def test_assigned_to_missing_is_none():
    t = parse_task_line('- [ ] **[Hi]** Solo task')
    assert t['assigned_to'] is None


# ---------------------------------------------------------------------------
# Context extraction (after —)
# ---------------------------------------------------------------------------

def test_context_extracted():
    t = parse_task_line('- [ ] **[Hi]** Call Jared — re: Q2 close timeline')
    assert t['context'] == 're: Q2 close timeline'
    assert t['text'] == 'Call Jared'


def test_no_context():
    t = parse_task_line('- [ ] **[Hi]** Call Jared')
    assert t['context'] == ''


# ---------------------------------------------------------------------------
# Completion date
# ---------------------------------------------------------------------------

def test_completion_date_extracted():
    t = parse_task_line('- [x] **[Hi]** Call Jared — completed 2026-03-01')
    assert t['completion_date'] == '2026-03-01'
    assert t['complete'] is True


def test_no_completion_date():
    t = parse_task_line('- [ ] **[Hi]** Call Jared')
    assert t['completion_date'] is None


# ---------------------------------------------------------------------------
# Strikethrough stripping
# ---------------------------------------------------------------------------

def test_strikethrough_stripped():
    t = parse_task_line('- [x] **[Low]** ~~Old task~~')
    assert t['text'] == 'Old task'


# ---------------------------------------------------------------------------
# Raw preserved
# ---------------------------------------------------------------------------

def test_raw_is_original_text():
    line = '- [ ] **[Hi]** Follow up (UTIMCO)'
    t = parse_task_line(line)
    assert t['raw'] == '**[Hi]** Follow up (UTIMCO)'


# ---------------------------------------------------------------------------
# Combined cases
# ---------------------------------------------------------------------------

def test_full_task_line():
    line = '- [ ] **[Hi]** **[→]** Follow up with Jared — check DD status — assigned:Paige'
    t = parse_task_line(line)
    assert t['priority'] == 'Hi'
    assert t['status'] == 'In Progress'
    assert t['assigned_to'] == 'Paige'
    assert 'assigned:' not in t['text']


def test_complete_task_with_org_and_context():
    line = '- [x] **[Med]** Sent deck (BlackRock) — completed 2026-02-28'
    t = parse_task_line(line)
    assert t['complete'] is True
    assert t['org'] == 'BlackRock'
    assert t['completion_date'] == '2026-02-28'
