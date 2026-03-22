"""email_matching.py — Participant/org matching utilities for email processing."""

import os
import yaml

from sources.crm_reader import find_person_by_email

# Internal AREC domains to skip
INTERNAL_DOMAINS = {
    "avilacapllc.com",
    "avilacapital.com",
    "builderadvisorgroup.com",
}

# Fundraising ally org domains — emails from these are pass-through, not direct matches.
# Note: individual ally emails (e.g. ilubert@belgravialp.com) are keyed by full address
# in crm/fundraising_allies.json, not by domain, because their domain belongs to a real prospect.
def _load_ally_domains() -> frozenset:
    """Load ally org domains from fundraising_allies.json at import time."""
    try:
        from sources.crm_reader import load_fundraising_allies
        allies = load_fundraising_allies()
        return frozenset(
            a["domain"].lower().lstrip("@")
            for a in allies.get("orgs", [])
            if a.get("domain")
        )
    except Exception:
        return frozenset()

ALLY_DOMAINS = _load_ally_domains()


def _get_user_email() -> str:
    """Get user email from config or env."""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f)
            if config and 'graph' in config:
                return config['graph'].get('user_email', '')
    return os.getenv('MS_USER_ID', 'oscar@avilacapllc.com')


def _is_internal(email: str) -> bool:
    if not email:
        return True
    email_lower = email.lower()
    domain = email_lower.split("@")[-1]
    if domain in INTERNAL_DOMAINS:
        return True
    user_email = _get_user_email().lower()
    if user_email and email_lower == user_email:
        return True
    return False


def _fuzzy_match_org(display_name: str, org_names: list[str]) -> str | None:
    """
    Substring fuzzy match: find a single org whose name appears in or contains
    the display name (≥6 character overlap). Also checks aliases.
    Returns canonical org name or None. If multiple orgs match, return None (ambiguous).
    """
    from sources.crm_reader import get_org_aliases_map, load_organizations

    display_lower = display_name.lower()
    matches = []

    # Build a combined candidate list: org names + all aliases
    # Each candidate maps to its canonical org name
    candidates = {}  # {search_string_lower: canonical_org_name}

    for org_name in org_names:
        candidates[org_name.lower()] = org_name

    # Add aliases
    alias_map = get_org_aliases_map()  # {alias_lower: canonical_org_name}
    for alias_lower, canonical_name in alias_map.items():
        # Only include if the canonical org is in org_names
        if canonical_name in org_names:
            candidates[alias_lower] = canonical_name

    # Fuzzy match against all candidates
    for candidate_lower, canonical_name in candidates.items():
        overlap = min(len(candidate_lower), len(display_lower))
        if overlap < 6:
            continue
        if candidate_lower in display_lower or display_lower in candidate_lower:
            if canonical_name not in matches:
                matches.append(canonical_name)

    if len(matches) == 1:
        return matches[0]
    return None


def _resolve_participant(email: str, display_name: str, all_org_names: list[str]) -> dict | None:
    """
    Try to resolve a participant (email + display name) to a CRM org.
    Returns {'org': name, 'contact': display_name} or None.
    """
    if _is_internal(email):
        return None

    # 1. Email exact match via person files
    person = find_person_by_email(email)
    if person:
        org = person.get("organization") or person.get("org", "")
        if org:
            return {"org": org, "contact": person.get("name", display_name)}

    # 2. Org name fuzzy match on display name
    org_match = _fuzzy_match_org(display_name, all_org_names)
    if org_match:
        return {"org": org_match, "contact": display_name}

    return None
