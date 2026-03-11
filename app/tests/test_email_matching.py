"""
test_email_matching.py — Tests for CRM email/participant matching logic.

Tests _fuzzy_match_org and _is_internal from crm_graph_sync.py.
_resolve_participant is tested with a mock for find_person_by_email.
"""

import os
import sys
import pytest
from unittest.mock import patch

# Ensure sources/ is importable
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from sources.crm_graph_sync import _fuzzy_match_org, _is_internal, _resolve_participant


# ---------------------------------------------------------------------------
# _fuzzy_match_org
# ---------------------------------------------------------------------------

ORG_LIST = [
    'UTIMCO',
    'Blackstone',
    'Merseyside Pension Fund',
    'RXR Realty',
    'Texas PSF',
    'Alpha Curve',
]


def test_exact_match():
    assert _fuzzy_match_org('UTIMCO', ORG_LIST) == 'UTIMCO'


def test_case_insensitive_match():
    assert _fuzzy_match_org('utimco', ORG_LIST) == 'UTIMCO'


def test_org_name_in_display_name():
    # Org name is a substring of display name
    assert _fuzzy_match_org('Blackstone TPM Group', ORG_LIST) == 'Blackstone'


def test_display_name_in_org_name():
    # Display name is a substring of org name
    assert _fuzzy_match_org('Merseyside', ORG_LIST) == 'Merseyside Pension Fund'


def test_multi_word_org_match():
    assert _fuzzy_match_org('Texas PSF Investment Committee', ORG_LIST) == 'Texas PSF'


def test_no_match_returns_none():
    assert _fuzzy_match_org('Goldman Sachs', ORG_LIST) is None


def test_ambiguous_match_returns_none():
    # Both 'RXR Realty' and 'Texas PSF' could fuzzy match if we had duplicates.
    # Simulate two orgs that both match the display name.
    ambiguous_orgs = ['RXR Capital', 'RXR Realty']
    # 'RXR' is only 3 chars — below the 6-char overlap threshold
    assert _fuzzy_match_org('RXR', ambiguous_orgs) is None


def test_short_name_below_threshold():
    # Org names strictly shorter than 6 chars are skipped by the threshold check.
    # 'AB' (2 chars) and 'XY' (2 chars) will not match anything.
    short_orgs = ['AB', 'XY']
    assert _fuzzy_match_org('AB Capital Partners', short_orgs) is None


def test_partial_overlap_at_threshold():
    # 'Alpha ' (6 chars) appears in 'Alpha Curve Capital'
    assert _fuzzy_match_org('Alpha Curve Capital', ORG_LIST) == 'Alpha Curve'


# ---------------------------------------------------------------------------
# _is_internal
# ---------------------------------------------------------------------------

def test_internal_avilacapllc_domain():
    assert _is_internal('oscar@avilacapllc.com') is True


def test_internal_avilacapital_domain():
    assert _is_internal('team@avilacapital.com') is True


def test_internal_builderadvisorgroup_domain():
    assert _is_internal('staff@builderadvisorgroup.com') is True


def test_external_email():
    assert _is_internal('jared@utimco.org') is False


def test_empty_email_treated_as_internal():
    # Empty email → skip (return True so it's filtered out)
    assert _is_internal('') is True


def test_none_email_treated_as_internal():
    assert _is_internal(None) is True


# ---------------------------------------------------------------------------
# _resolve_participant
# ---------------------------------------------------------------------------

def test_resolve_by_exact_email_match():
    """Person file lookup returns an org → use it."""
    mock_person = {'name': 'Jared Brimberry', 'organization': 'UTIMCO', 'email': 'jared@utimco.org'}
    with patch('sources.crm_graph_sync.find_person_by_email', return_value=mock_person):
        result = _resolve_participant('jared@utimco.org', 'Jared Brimberry', ORG_LIST)
    assert result == {'org': 'UTIMCO', 'contact': 'Jared Brimberry'}


def test_resolve_by_fuzzy_display_name_when_no_person_file():
    """No person file → fall back to fuzzy org match on display name."""
    with patch('sources.crm_graph_sync.find_person_by_email', return_value=None):
        result = _resolve_participant('unknown@blackstone.com', 'Blackstone Portfolio', ORG_LIST)
    assert result == {'org': 'Blackstone', 'contact': 'Blackstone Portfolio'}


def test_resolve_returns_none_for_internal_email():
    """Internal email → skip (return None)."""
    with patch('sources.crm_graph_sync.find_person_by_email', return_value=None):
        result = _resolve_participant('oscar@avilacapllc.com', 'Oscar Vasquez', ORG_LIST)
    assert result is None


def test_resolve_returns_none_when_no_match():
    """No person file AND no fuzzy org match → None."""
    with patch('sources.crm_graph_sync.find_person_by_email', return_value=None):
        result = _resolve_participant('stranger@noreply.com', 'Newsletter Bot', ORG_LIST)
    assert result is None


def test_resolve_uses_person_name_not_display_name():
    """When person file found, return person's stored name, not the raw display name."""
    mock_person = {'name': 'Jared C. Brimberry', 'organization': 'UTIMCO', 'email': 'jared@utimco.org'}
    with patch('sources.crm_graph_sync.find_person_by_email', return_value=mock_person):
        result = _resolve_participant('jared@utimco.org', 'J. Brimberry', ORG_LIST)
    assert result['contact'] == 'Jared C. Brimberry'
