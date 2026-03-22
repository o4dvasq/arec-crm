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


# ---------------------------------------------------------------------------
# Fundraising ally helpers (crm_reader.is_ally_org, is_ally_email)
# ---------------------------------------------------------------------------

MOCK_ALLIES = {
    "version": 1,
    "orgs": [
        {"name": "South40 Capital", "domain": "south40capital.com", "type": "Placement Agent"},
        {"name": "Angeloni & Co", "domain": "angeloniandco.com", "type": "Placement Agent"},
        {"name": "JTP Capital", "domain": "jtpllc.com", "type": "Placement Agent"},
    ],
    "individuals": [
        {"name": "Scott Richland", "email": "scott@lunadabayinv.com", "org": "Scott Richland",
         "type": "INTRODUCER", "notes": ""},
        {"name": "Ira Lubert", "email": "ilubert@belgravialp.com", "org": "Belgravia Management",
         "type": "INTRODUCER", "notes": "belgravialp.com is a real prospect domain"},
    ],
}


def test_is_ally_org_returns_true_for_placement_agent():
    """is_ally_org returns True for known ally org names."""
    from sources.crm_reader import is_ally_org
    with patch('sources.crm_reader.load_fundraising_allies', return_value=MOCK_ALLIES):
        assert is_ally_org("South40 Capital") is True
        assert is_ally_org("Angeloni & Co") is True
        assert is_ally_org("JTP Capital") is True


def test_is_ally_org_returns_false_for_real_prospect():
    """is_ally_org returns False for orgs not in the allies list."""
    from sources.crm_reader import is_ally_org
    with patch('sources.crm_reader.load_fundraising_allies', return_value=MOCK_ALLIES):
        assert is_ally_org("Belgravia Management") is False
        assert is_ally_org("UTIMCO") is False


def test_is_ally_org_case_insensitive():
    """is_ally_org is case-insensitive."""
    from sources.crm_reader import is_ally_org
    with patch('sources.crm_reader.load_fundraising_allies', return_value=MOCK_ALLIES):
        assert is_ally_org("south40 capital") is True
        assert is_ally_org("ANGELONI & CO") is True


def test_is_ally_email_returns_true_for_individual_ally():
    """is_ally_email returns True for known individual ally email addresses."""
    from sources.crm_reader import is_ally_email
    with patch('sources.crm_reader.load_fundraising_allies', return_value=MOCK_ALLIES):
        assert is_ally_email("scott@lunadabayinv.com") is True
        assert is_ally_email("ilubert@belgravialp.com") is True


def test_is_ally_email_returns_false_for_non_ally():
    """is_ally_email returns False for emails not in the individual allies list."""
    from sources.crm_reader import is_ally_email
    with patch('sources.crm_reader.load_fundraising_allies', return_value=MOCK_ALLIES):
        assert is_ally_email("jsmith@belgravialp.com") is False
        assert is_ally_email("oscar@avilacapllc.com") is False


def test_lubert_email_keyed_not_domain_keyed():
    """Ira Lubert's specific email is ally, but other @belgravialp.com addresses are not."""
    from sources.crm_reader import is_ally_email
    with patch('sources.crm_reader.load_fundraising_allies', return_value=MOCK_ALLIES):
        # Ira's specific email → ally
        assert is_ally_email("ilubert@belgravialp.com") is True
        # Different person at same domain → NOT ally (Belgravia is a real Stage 7 prospect)
        assert is_ally_email("jdoe@belgravialp.com") is False
        assert is_ally_email("info@belgravialp.com") is False


# ---------------------------------------------------------------------------
# match_email_to_org ally pass-through (graph_poller)
# ---------------------------------------------------------------------------

def _make_msg(sender_email: str, sender_name: str = "", recipients: list = None) -> dict:
    """Build a minimal Graph message dict for testing match_email_to_org."""
    to_recipients = [
        {"emailAddress": {"address": r, "name": r}} for r in (recipients or [])
    ]
    return {
        "id": "test-msg-id",
        "subject": "Test Subject",
        "from": {"emailAddress": {"address": sender_email, "name": sender_name}},
        "toRecipients": to_recipients,
        "ccRecipients": [],
        "receivedDateTime": "2026-03-22T10:00:00Z",
    }


def test_ally_inbound_passthrough_finds_real_prospect():
    """Inbound from ally org (South40) → scans recipients → returns real prospect org."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from graph_poller import match_email_to_org

    msg = _make_msg(
        sender_email="ian@south40capital.com",
        sender_name="Ian Morgan",
        recipients=["oscar@avilacapllc.com", "jbrimberry@utimco.org"],
    )

    with patch('graph_poller.is_ally_email', return_value=False), \
         patch('graph_poller.get_org_by_domain', side_effect=lambda d: {
             "south40capital.com": "South40 Capital",
             "utimco.org": "UTIMCO",
         }.get(d)), \
         patch('graph_poller.is_ally_org', side_effect=lambda o: o == "South40 Capital"), \
         patch('graph_poller.find_person_by_email', return_value=None), \
         patch('graph_poller.get_individual_ally_name', return_value=None):
        result = match_email_to_org(msg)

    assert result is not None
    assert result["org"] == "UTIMCO"
    assert result["via_ally"] == "South40 Capital"


def test_ally_only_email_returns_none():
    """Email with only ally participants (no real prospect) → returns None, skipped."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from graph_poller import match_email_to_org

    msg = _make_msg(
        sender_email="max@angeloniandco.com",
        sender_name="Max Angeloni",
        recipients=["oscar@avilacapllc.com", "tony@avilacapllc.com"],
    )

    with patch('graph_poller.is_ally_email', return_value=False), \
         patch('graph_poller.get_org_by_domain', side_effect=lambda d: {
             "angeloniandco.com": "Angeloni & Co",
         }.get(d)), \
         patch('graph_poller.is_ally_org', side_effect=lambda o: o == "Angeloni & Co"), \
         patch('graph_poller.find_person_by_email', return_value=None), \
         patch('graph_poller.get_individual_ally_name', return_value=None):
        result = match_email_to_org(msg)

    assert result is None


def test_lubert_inbound_passthrough():
    """Ira Lubert's email triggers individual-ally pass-through even though domain matches Belgravia."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from graph_poller import match_email_to_org

    msg = _make_msg(
        sender_email="ilubert@belgravialp.com",
        sender_name="Ira Lubert",
        recipients=["oscar@avilacapllc.com", "jdoe@iowapersra.org"],
    )

    with patch('graph_poller.is_ally_email', side_effect=lambda e: e == "ilubert@belgravialp.com"), \
         patch('graph_poller.get_org_by_domain', side_effect=lambda d: {
             "belgravialp.com": "Belgravia Management",
             "iowapersra.org": "Iowa PERS",
         }.get(d)), \
         patch('graph_poller.is_ally_org', return_value=False), \
         patch('graph_poller.find_person_by_email', return_value=None), \
         patch('graph_poller.get_individual_ally_name', return_value="Ira Lubert"):
        result = match_email_to_org(msg)

    assert result is not None
    assert result["org"] == "Iowa PERS"
    assert result["via_ally"] == "Ira Lubert"


def test_other_belgravia_email_matches_belgravia_directly():
    """Non-Ira @belgravialp.com email matches Belgravia Management directly (no pass-through)."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from graph_poller import match_email_to_org

    msg = _make_msg(
        sender_email="jsmith@belgravialp.com",
        sender_name="John Smith",
        recipients=["oscar@avilacapllc.com"],
    )

    with patch('graph_poller.is_ally_email', return_value=False), \
         patch('graph_poller.get_org_by_domain', side_effect=lambda d: {
             "belgravialp.com": "Belgravia Management",
         }.get(d)), \
         patch('graph_poller.is_ally_org', return_value=False), \
         patch('graph_poller.find_person_by_email', return_value=None), \
         patch('graph_poller.get_individual_ally_name', return_value=None):
        result = match_email_to_org(msg)

    assert result is not None
    assert result["org"] == "Belgravia Management"
    assert result.get("via_ally") is None
