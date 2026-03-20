"""
test_email_matching.py — Tests for CRM email/participant matching logic.

Tests _fuzzy_match_org and _is_internal from email_matching.py.
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

from sources.email_matching import _fuzzy_match_org, _is_internal, _resolve_participant


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
    with patch('sources.email_matching.find_person_by_email', return_value=mock_person):
        result = _resolve_participant('jared@utimco.org', 'Jared Brimberry', ORG_LIST)
    assert result == {'org': 'UTIMCO', 'contact': 'Jared Brimberry'}


def test_resolve_by_fuzzy_display_name_when_no_person_file():
    """No person file → fall back to fuzzy org match on display name."""
    with patch('sources.email_matching.find_person_by_email', return_value=None):
        result = _resolve_participant('unknown@blackstone.com', 'Blackstone Portfolio', ORG_LIST)
    assert result == {'org': 'Blackstone', 'contact': 'Blackstone Portfolio'}


def test_resolve_returns_none_for_internal_email():
    """Internal email → skip (return None)."""
    with patch('sources.email_matching.find_person_by_email', return_value=None):
        result = _resolve_participant('oscar@avilacapllc.com', 'Oscar Vasquez', ORG_LIST)
    assert result is None


def test_resolve_returns_none_when_no_match():
    """No person file AND no fuzzy org match → None."""
    with patch('sources.email_matching.find_person_by_email', return_value=None):
        result = _resolve_participant('stranger@noreply.com', 'Newsletter Bot', ORG_LIST)
    assert result is None


def test_resolve_uses_person_name_not_display_name():
    """When person file found, return person's stored name, not the raw display name."""
    mock_person = {'name': 'Jared C. Brimberry', 'organization': 'UTIMCO', 'email': 'jared@utimco.org'}
    with patch('sources.email_matching.find_person_by_email', return_value=mock_person):
        result = _resolve_participant('jared@utimco.org', 'J. Brimberry', ORG_LIST)
    assert result['contact'] == 'Jared C. Brimberry'


# ---------------------------------------------------------------------------
# _fuzzy_match_org with aliases
# ---------------------------------------------------------------------------

def test_fuzzy_match_with_alias():
    """Display name containing an alias should resolve to canonical org name."""
    mock_alias_map = {
        'massmutual': 'Mass Mutual Life Insurance Co.',
        'mmlic': 'Mass Mutual Life Insurance Co.',
    }
    orgs_with_aliases = ['Mass Mutual Life Insurance Co.', 'Blackstone']

    with patch('sources.crm_reader.get_org_aliases_map', return_value=mock_alias_map):
        with patch('sources.crm_reader.load_organizations'):
            result = _fuzzy_match_org('MassMutual Investment Group', orgs_with_aliases)

    assert result == 'Mass Mutual Life Insurance Co.'


def test_fuzzy_match_alias_case_insensitive():
    """Alias matching is case-insensitive in fuzzy match."""
    mock_alias_map = {
        'massmutual': 'Mass Mutual Life Insurance Co.',  # 10 chars - above threshold
    }
    orgs_with_aliases = ['Mass Mutual Life Insurance Co.']

    with patch('sources.crm_reader.get_org_aliases_map', return_value=mock_alias_map):
        with patch('sources.crm_reader.load_organizations'):
            result = _fuzzy_match_org('MASSMUTUAL Investments', orgs_with_aliases)

    assert result == 'Mass Mutual Life Insurance Co.'


def test_fuzzy_match_alias_respects_6_char_threshold():
    """Aliases below 6 chars should not match (same threshold as org names)."""
    mock_alias_map = {
        'abc': 'ABC Corp',  # Only 3 chars
    }
    orgs_with_aliases = ['ABC Corp']

    with patch('sources.crm_reader.get_org_aliases_map', return_value=mock_alias_map):
        with patch('sources.crm_reader.load_organizations'):
            result = _fuzzy_match_org('ABC Capital Partners', orgs_with_aliases)

    # Should not match because 'abc' is below the 6-char threshold
    assert result is None


def test_fuzzy_match_prefers_canonical_name_over_alias():
    """When both canonical name and alias could match, should still return single result."""
    mock_alias_map = {
        'stepstone group': 'StepStone',
    }
    orgs_with_aliases = ['StepStone']

    with patch('sources.crm_reader.get_org_aliases_map', return_value=mock_alias_map):
        with patch('sources.crm_reader.load_organizations'):
            # This display name contains the alias
            result = _fuzzy_match_org('StepStone Group Holdings', orgs_with_aliases)

    assert result == 'StepStone'


def test_fuzzy_match_multiple_aliases_same_org():
    """Multiple aliases for the same org should still resolve to single canonical name."""
    mock_alias_map = {
        'massmutual': 'Mass Mutual Life Insurance Co.',
        'mass mutual': 'Mass Mutual Life Insurance Co.',
    }
    orgs_with_aliases = ['Mass Mutual Life Insurance Co.']

    with patch('sources.crm_reader.get_org_aliases_map', return_value=mock_alias_map):
        with patch('sources.crm_reader.load_organizations'):
            # Match via second alias (case-insensitive)
            result = _fuzzy_match_org('MASS MUTUAL Portfolio', orgs_with_aliases)

    assert result == 'Mass Mutual Life Insurance Co.'


def test_fuzzy_match_no_alias_match_returns_none():
    """When no alias or org name matches, return None."""
    mock_alias_map = {
        'massmutual': 'Mass Mutual Life Insurance Co.',
    }
    orgs_with_aliases = ['Mass Mutual Life Insurance Co.']

    with patch('sources.crm_reader.get_org_aliases_map', return_value=mock_alias_map):
        with patch('sources.crm_reader.load_organizations'):
            result = _fuzzy_match_org('Goldman Sachs', orgs_with_aliases)

    assert result is None
