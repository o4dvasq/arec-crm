"""
test_resolve_org_name.py — Tests for org name normalization via aliases.

Tests the resolve_org_name() function from crm_reader.py.
"""

import os
import sys
import pytest
from unittest.mock import patch

# Ensure sources/ is importable
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from sources.crm_reader import resolve_org_name


# Mock organizations data for testing
MOCK_ORGS = [
    {
        'name': 'Mass Mutual Life Insurance Co.',
        'Aliases': 'MassMutual, MMLIC',
    },
    {
        'name': 'StepStone',
        'Aliases': 'StepStone Group',
    },
    {
        'name': 'Pennsylvania Public School Employees\' Retirement System',
        'Aliases': 'PSERS',
    },
    {
        'name': 'UTIMCO',
        'Aliases': '',  # No aliases
    },
]


def mock_load_organizations():
    """Return mock org data."""
    return MOCK_ORGS


def mock_get_org_by_alias(alias):
    """Simple alias lookup matching the mock data."""
    if not alias:
        return None
    alias_lower = alias.strip().lower()
    for org in MOCK_ORGS:
        aliases_raw = org.get('Aliases', '')
        if aliases_raw:
            aliases = [a.strip() for a in aliases_raw.split(',') if a.strip()]
            for a in aliases:
                if a.lower() == alias_lower:
                    return org['name']
    return None


# ---------------------------------------------------------------------------
# resolve_org_name tests
# ---------------------------------------------------------------------------

@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_exact_org_name_match():
    """Exact match on canonical org name returns canonical name with correct casing."""
    assert resolve_org_name('UTIMCO') == 'UTIMCO'


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_case_insensitive_org_name_match():
    """Case-insensitive match on canonical org name returns canonical casing."""
    assert resolve_org_name('utimco') == 'UTIMCO'


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_alias_resolves_to_canonical_name():
    """Alias 'MassMutual' resolves to canonical name."""
    assert resolve_org_name('MassMutual') == 'Mass Mutual Life Insurance Co.'


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_alias_case_insensitive():
    """Alias matching is case-insensitive."""
    assert resolve_org_name('massmutual') == 'Mass Mutual Life Insurance Co.'
    assert resolve_org_name('MASSMUTUAL') == 'Mass Mutual Life Insurance Co.'


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_stepstone_group_alias():
    """'StepStone Group' alias resolves to 'StepStone'."""
    assert resolve_org_name('StepStone Group') == 'StepStone'


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_psers_alias():
    """'PSERS' alias resolves to long canonical name."""
    assert resolve_org_name('PSERS') == 'Pennsylvania Public School Employees\' Retirement System'


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_unknown_name_passes_through():
    """Unknown org name returns the original name unchanged."""
    assert resolve_org_name('Unknown Corp') == 'Unknown Corp'


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_empty_string_returns_empty():
    """Empty string returns empty string."""
    assert resolve_org_name('') == ''


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_whitespace_only_returns_whitespace():
    """Whitespace-only string returns the original whitespace."""
    assert resolve_org_name('   ') == '   '


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_whitespace_trimmed_before_match():
    """Leading/trailing whitespace is trimmed before matching."""
    assert resolve_org_name('  UTIMCO  ') == 'UTIMCO'


@patch('sources.crm_reader.load_organizations', mock_load_organizations)
@patch('sources.crm_reader.get_org_by_alias', mock_get_org_by_alias)
def test_idempotent():
    """resolve_org_name is idempotent: resolving a resolved name returns the same name."""
    canonical = resolve_org_name('MassMutual')
    assert resolve_org_name(canonical) == canonical
