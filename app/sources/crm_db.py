"""
CRM data reader/writer backed by PostgreSQL (SQLAlchemy).

Drop-in replacement for crm_reader.py. All function signatures match exactly.
All downstream consumers import from here.
"""

import os
import re
import json
from datetime import date, datetime, timedelta
from typing import Optional

from models import (
    Organization, Offering, Contact, Prospect, Interaction, EmailScanLog,
    Brief, ProspectNote, UnmatchedEmail, PendingInterview, User, PipelineStage,
    ProspectTask, UrgencyLevel, ClosingOption, InteractionType, InteractionSource
)
from db import get_session, session_scope

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(APP_ROOT)
PEOPLE_ROOT = os.path.join(PROJECT_ROOT, "memory", "people")
TASKS_MD_PATH = os.path.join(PROJECT_ROOT, "TASKS.md")

# Field write order for prospects (matches crm_reader.py)
PROSPECT_FIELD_ORDER = [
    "Stage", "Target", "Primary Contact",
    "Closing", "Urgent", "Assigned To", "Notes", "Last Touch"
]

BRIEF_FIELDS = ['Relationship Brief', 'Brief Refreshed']
BRIEF_FIELD_MAP = {
    'relationship brief': 'Relationship Brief',
    'brief refreshed': 'Brief Refreshed',
}

EDITABLE_FIELDS = {
    'stage', 'urgent', 'target', 'assigned_to',
    'notes', 'closing', 'primary_contact'
}

# Domains to exclude (matches crm_reader.py)
_INTERNAL_DOMAINS = {"avilacapllc.com", "avilacapital.com", "builderadvisorgroup.com"}
_GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "me.com", "live.com", "msn.com", "protonmail.com",
    "mail.com", "zoho.com",
}
_SERVICE_PROVIDER_ORGS = {
    "Clifford Chance", "South40 Capital", "Greshler Finance",
    "First Forte", "Maples",
}


# ---------------------------------------------------------------------------
# Currency helpers (pure functions, copied from crm_reader.py)
# ---------------------------------------------------------------------------

def _format_currency(n: float) -> str:
    """50000000 → '$50M', 1500000000 → '$1.5B'"""
    if n == 0:
        return "$0"
    if n >= 1_000_000_000:
        val = n / 1_000_000_000
        return f"${val:.2f}B"
    if n >= 1_000_000:
        val = n / 1_000_000
        formatted = f"{val:g}"
        return f"${formatted}M"
    if n >= 1_000:
        val = n / 1_000
        formatted = f"{val:g}"
        return f"${formatted}K"
    return f"${n:,.0f}"


def _parse_currency(s: str) -> float:
    """'$50,000,000' → 50000000.0, '$50M' → 50000000.0"""
    if not s or str(s).strip() in ('', '$0', '$'):
        return 0.0
    s = str(s).strip().replace(',', '').replace('$', '').strip()
    multipliers = {'B': 1_000_000_000, 'M': 1_000_000, 'K': 1_000}
    for suffix, mult in multipliers.items():
        if s.upper().endswith(suffix):
            try:
                return float(s[:-1]) * mult
            except ValueError:
                return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _urgency_to_str(urgency: Optional[UrgencyLevel]) -> str:
    """Convert UrgencyLevel enum to string for display."""
    if urgency == UrgencyLevel.High:
        return "Yes"
    elif urgency == UrgencyLevel.Med:
        return "Med"
    elif urgency == UrgencyLevel.Low:
        return "Low"
    return ""


def _closing_to_str(closing: Optional[ClosingOption]) -> str:
    """Convert ClosingOption enum to string."""
    if closing == ClosingOption.First:
        return "1st"
    elif closing == ClosingOption.Second:
        return "2nd"
    elif closing == ClosingOption.Final:
        return "Final"
    return ""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_crm_config() -> dict:
    """Return CRM configuration from pipeline_stages table + hardcoded lists."""
    session = get_session()
    try:
        # Load pipeline stages from DB
        stages_objs = session.query(PipelineStage).order_by(PipelineStage.sort_order).all()
        stages = [f"{s.number}. {s.name.split('. ', 1)[-1]}" for s in stages_objs]
        terminal_stages = [f"{s.number}. {s.name.split('. ', 1)[-1]}" for s in stages_objs if s.is_terminal]

        # Load team from users table
        users = session.query(User).filter_by(is_active=True).all()
        team_list = [{'name': u.display_name, 'email': u.email} for u in users]
        team_map = [
            {'short': u.display_name.split()[0], 'full': u.display_name, 'email': u.email}
            for u in users
        ]

        # Hardcoded org types (19 distinct values from spec)
        org_types = [
            'HNWI / FO', 'Asset Manager', 'Bank', 'Endowment', 'Pension Fund',
            'Foundation', 'Insurance Company', 'Sovereign Wealth Fund',
            'Corporate Pension', 'Public Pension', 'Family Office', 'Fund of Funds',
            'Consultant', 'Advisor', 'OCIO', 'Multi-Family Office', 'RIA',
            'Private Bank', 'Other'
        ]

        return {
            'stages': stages,
            'terminal_stages': terminal_stages,
            'org_types': org_types,
            'closing_options': ['1st', '2nd', 'Final'],
            'urgency_levels': ['Yes', 'Med', 'Low'],
            'team': team_list,
            'team_map': team_map,
            'delegate_mailboxes': [],  # Not migrated in Phase I1
        }
    finally:
        session.close()


def get_team_member_email(name: str) -> str:
    """Look up email for an AREC team member by name."""
    if not name:
        return ''
    session = get_session()
    try:
        name_lower = name.lower().strip()
        # Try exact match first
        user = session.query(User).filter(User.display_name.ilike(name_lower)).first()
        if user:
            return user.email
        # Try partial match
        user = session.query(User).filter(User.display_name.ilike(f'%{name_lower}%')).first()
        if user:
            return user.email
        return ''
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Offerings
# ---------------------------------------------------------------------------

def load_offerings() -> list[dict]:
    """Load all offerings."""
    session = get_session()
    try:
        offerings = session.query(Offering).all()
        return [
            {
                'name': o.name,
                'Target': _format_currency(o.target / 100) if o.target else '$0',
                'Hard Cap': _format_currency(o.hard_cap / 100) if o.hard_cap else '',
            }
            for o in offerings
        ]
    finally:
        session.close()


def get_offering(name: str) -> dict | None:
    """Get a single offering by name."""
    session = get_session()
    try:
        offering = session.query(Offering).filter(Offering.name.ilike(name)).first()
        if not offering:
            return None
        return {
            'name': offering.name,
            'Target': _format_currency(offering.target / 100) if offering.target else '$0',
            'Hard Cap': _format_currency(offering.hard_cap / 100) if offering.hard_cap else '',
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

def load_organizations() -> list[dict]:
    """Load all organizations."""
    session = get_session()
    try:
        orgs = session.query(Organization).order_by(Organization.name).all()
        return [
            {
                'name': o.name,
                'Type': o.type,
                'Domain': o.domain,
                'Notes': o.notes,
            }
            for o in orgs
        ]
    finally:
        session.close()


def get_organization(name: str) -> dict | None:
    """Get a single organization by name."""
    session = get_session()
    try:
        org = session.query(Organization).filter(Organization.name.ilike(name)).first()
        if not org:
            return None
        return {
            'name': org.name,
            'Type': org.type,
            'Domain': org.domain,
            'Notes': org.notes,
        }
    finally:
        session.close()


def write_organization(name: str, data: dict) -> None:
    """Update fields for an existing org or create new."""
    session = get_session()
    try:
        org = session.query(Organization).filter(Organization.name.ilike(name)).first()
        if org:
            if 'Type' in data:
                org.type = data['Type']
            if 'Domain' in data:
                org.domain = data['Domain']
            if 'Notes' in data:
                org.notes = data['Notes']
            org.updated_at = datetime.now()
        else:
            org = Organization(
                name=name,
                type=data.get('Type', ''),
                domain=data.get('Domain', ''),
                notes=data.get('Notes', '')
            )
            session.add(org)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_organization(name: str) -> None:
    """Delete an organization."""
    session = get_session()
    try:
        org = session.query(Organization).filter(Organization.name.ilike(name)).first()
        if org:
            session.delete(org)
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

def load_contacts_index() -> dict:
    """Returns {org_name: [slug, ...]} for backward compat.

    In Phase I1, contacts are in DB not markdown files. Return org → contact name mapping.
    """
    session = get_session()
    try:
        orgs = session.query(Organization).all()
        result = {}
        for org in orgs:
            contacts = session.query(Contact).filter_by(organization_id=org.id).all()
            # Use slugified name as "slug" for backward compat
            result[org.name] = [_name_to_slug(c.name) for c in contacts]
        return result
    finally:
        session.close()


def load_person(slug: str) -> dict | None:
    """Load contact by slug (slugified name). Phase I1: queries contacts table."""
    session = get_session()
    try:
        # Reverse-engineer name from slug
        name_guess = slug.replace('-', ' ').title()
        contact = session.query(Contact).filter(Contact.name.ilike(name_guess)).first()
        if not contact:
            return None

        org = session.query(Organization).filter_by(id=contact.organization_id).first()
        return {
            'slug': slug,
            'name': contact.name,
            'organization': org.name if org else '',
            'role': contact.title,
            'email': contact.email,
            'phone': contact.phone,
            'type': 'investor',  # Default type
        }
    finally:
        session.close()


def get_contacts_for_org(org_name: str) -> list[dict]:
    """Return list of contact dicts for an org."""
    session = get_session()
    try:
        org = session.query(Organization).filter(Organization.name.ilike(org_name)).first()
        if not org:
            return []
        contacts = session.query(Contact).filter_by(organization_id=org.id).all()
        return [
            {
                'slug': _name_to_slug(c.name),
                'name': c.name,
                'organization': org_name,
                'role': c.title,
                'email': c.email,
                'phone': c.phone,
                'type': 'investor',
            }
            for c in contacts
        ]
    finally:
        session.close()


def find_person_by_email(email: str) -> dict | None:
    """Search all contacts for a matching email."""
    if not email:
        return None
    session = get_session()
    try:
        contact = session.query(Contact).filter(Contact.email.ilike(email)).first()
        if not contact:
            return None
        org = session.query(Organization).filter_by(id=contact.organization_id).first()
        return {
            'slug': _name_to_slug(contact.name),
            'name': contact.name,
            'organization': org.name if org else '',
            'role': contact.title,
            'email': contact.email,
            'phone': contact.phone,
            'type': 'investor',
        }
    finally:
        session.close()


def _name_to_slug(name: str) -> str:
    """Convert 'Susannah Friar' → 'susannah-friar'"""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def create_person_file(name: str, org: str, email: str, role: str, person_type: str) -> str:
    """Create a contact in the DB. Returns slug."""
    session = get_session()
    try:
        org_obj = session.query(Organization).filter(Organization.name.ilike(org)).first()
        if not org_obj:
            raise ValueError(f"Organization not found: {org}")

        slug = _name_to_slug(name)

        # Check if contact already exists
        contact = session.query(Contact).filter_by(
            name=name, organization_id=org_obj.id
        ).first()

        if not contact:
            contact = Contact(
                name=name,
                organization_id=org_obj.id,
                title=role,
                email=email,
                phone='',
                notes=''
            )
            session.add(contact)
            session.commit()

        return slug
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def load_all_persons() -> list[dict]:
    """Load all contacts from DB, sorted by name."""
    session = get_session()
    try:
        contacts = session.query(Contact).order_by(Contact.name).all()
        result = []
        for c in contacts:
            org = session.query(Organization).filter_by(id=c.organization_id).first()
            result.append({
                'slug': _name_to_slug(c.name),
                'name': c.name,
                'organization': org.name if org else '',
                'role': c.title,
                'email': c.email,
                'phone': c.phone,
                'type': 'investor',
            })
        return result
    finally:
        session.close()


def enrich_person_email(slug: str, email: str) -> None:
    """Update the email field for a contact."""
    session = get_session()
    try:
        name_guess = slug.replace('-', ' ').title()
        contact = session.query(Contact).filter(Contact.name.ilike(name_guess)).first()
        if contact:
            contact.email = email
            contact.updated_at = datetime.now()
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def add_contact_to_index(org: str, slug: str) -> None:
    """Phase I1: No-op (contacts are in DB, not index file)."""
    pass


def ensure_contact_linked(name: str, org: str) -> None:
    """Ensure a contact exists in the DB for this org."""
    if not name or not org:
        return
    session = get_session()
    try:
        org_obj = session.query(Organization).filter(Organization.name.ilike(org)).first()
        if not org_obj:
            return

        # Check if contact exists
        contact = session.query(Contact).filter(
            Contact.organization_id == org_obj.id,
            Contact.name.ilike(name)
        ).first()

        if not contact:
            contact = Contact(
                name=name,
                organization_id=org_obj.id,
                title='',
                email='',
                phone='',
                notes=''
            )
            session.add(contact)
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_contact_fields(org: str, name: str, fields: dict) -> bool:
    """Update editable fields on a contact."""
    session = get_session()
    try:
        org_obj = session.query(Organization).filter(Organization.name.ilike(org)).first()
        if not org_obj:
            return False

        contact = session.query(Contact).filter(
            Contact.organization_id == org_obj.id,
            Contact.name.ilike(name)
        ).first()

        if not contact:
            return False

        if 'role' in fields or 'title' in fields:
            contact.title = fields.get('role', fields.get('title', contact.title))
        if 'email' in fields:
            contact.email = fields['email']
        if 'phone' in fields:
            contact.phone = fields['phone']

        contact.updated_at = datetime.now()
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Prospects
# ---------------------------------------------------------------------------

def load_prospects(offering: str = None) -> list[dict]:
    """Load all prospects, optionally filtered by offering name."""
    session = get_session()
    try:
        query = session.query(Prospect)
        if offering:
            off_obj = session.query(Offering).filter(Offering.name.ilike(offering)).first()
            if off_obj:
                query = query.filter_by(offering_id=off_obj.id)

        prospects = query.all()
        result = []

        for p in prospects:
            org = session.query(Organization).filter_by(id=p.organization_id).first()
            off = session.query(Offering).filter_by(id=p.offering_id).first()
            contact = session.query(Contact).filter_by(id=p.primary_contact_id).first() if p.primary_contact_id else None
            assignee = session.query(User).filter_by(id=p.assigned_to).first() if p.assigned_to else None

            result.append({
                'org': org.name if org else '',
                'offering': off.name if off else '',
                'disambiguator': p.disambiguator,
                'Stage': p.stage,
                'Target': _format_currency(p.target / 100),
                'Committed': _format_currency(p.committed / 100),
                'Primary Contact': contact.name if contact else '',
                'Closing': _closing_to_str(p.closing),
                'Urgent': _urgency_to_str(p.urgency),
                'Assigned To': assignee.display_name if assignee else '',
                'Notes': p.notes,
                'Last Touch': p.last_touch.isoformat() if p.last_touch else '',
                'Relationship Brief': p.relationship_brief,
                'urgent': p.urgency == UrgencyLevel.High,  # Boolean for templates
            })

        return result
    finally:
        session.close()


def get_prospect(org: str, offering: str) -> dict | None:
    """Get a single prospect by org and offering."""
    for p in load_prospects(offering):
        if p['org'].lower() == org.lower():
            return p
    return None


def get_prospects_for_org(org: str) -> list[dict]:
    """Return all prospects for this org across all offerings."""
    return [p for p in load_prospects() if p['org'].lower() == org.lower()]


def write_prospect(org: str, offering: str, data: dict) -> None:
    """Write or update a prospect record."""
    session = get_session()
    try:
        org_obj = session.query(Organization).filter(Organization.name.ilike(org)).first()
        off_obj = session.query(Offering).filter(Offering.name.ilike(offering)).first()

        if not org_obj or not off_obj:
            raise ValueError(f"Org or offering not found: {org}, {offering}")

        disambiguator = data.get('disambiguator')
        prospect = session.query(Prospect).filter_by(
            organization_id=org_obj.id,
            offering_id=off_obj.id,
            disambiguator=disambiguator
        ).first()

        # Parse fields
        stage = data.get('Stage', '1. Prospect')
        target_str = data.get('Target', '$0')
        target_cents = int(_parse_currency(target_str) * 100)

        committed_str = data.get('Committed', '$0')
        committed_cents = int(_parse_currency(committed_str) * 100)

        # Parse urgency
        urgent_str = data.get('Urgent', '').strip()
        urgency = None
        if urgent_str:
            if urgent_str.lower() in ('yes', 'high'):
                urgency = UrgencyLevel.High
            elif urgent_str.lower() == 'med':
                urgency = UrgencyLevel.Med
            elif urgent_str.lower() == 'low':
                urgency = UrgencyLevel.Low

        # Parse closing
        closing_str = data.get('Closing', '').strip()
        closing = None
        if closing_str:
            if '1st' in closing_str.lower():
                closing = ClosingOption.First
            elif '2nd' in closing_str.lower():
                closing = ClosingOption.Second
            elif 'final' in closing_str.lower():
                closing = ClosingOption.Final

        # Find assigned user
        assigned_to_id = None
        assigned_str = data.get('Assigned To', '').strip()
        if assigned_str:
            first_name = assigned_str.split(';')[0].strip()
            user = session.query(User).filter(User.display_name.ilike(f'%{first_name}%')).first()
            if user:
                assigned_to_id = user.id

        # Find primary contact
        primary_contact_id = None
        contact_str = data.get('Primary Contact', '').strip()
        if contact_str:
            first_contact_name = contact_str.replace(';', ',').split(',')[0].strip()
            contact = session.query(Contact).filter(
                Contact.organization_id == org_obj.id,
                Contact.name.ilike(f'%{first_contact_name}%')
            ).first()
            if contact:
                primary_contact_id = contact.id

        notes = data.get('Notes', '')
        last_touch_str = data.get('Last Touch', '')
        last_touch = None
        if last_touch_str:
            try:
                last_touch = datetime.fromisoformat(last_touch_str).date()
            except (ValueError, TypeError):
                pass

        relationship_brief = data.get('Relationship Brief', '')

        if prospect:
            # Update existing
            prospect.stage = stage
            prospect.target = target_cents
            prospect.committed = committed_cents
            prospect.urgency = urgency
            prospect.closing = closing
            prospect.assigned_to = assigned_to_id
            prospect.primary_contact_id = primary_contact_id
            prospect.notes = notes
            prospect.last_touch = last_touch
            prospect.relationship_brief = relationship_brief
            prospect.updated_at = datetime.now()
        else:
            # Create new
            prospect = Prospect(
                organization_id=org_obj.id,
                offering_id=off_obj.id,
                stage=stage,
                target=target_cents,
                committed=committed_cents,
                urgency=urgency,
                closing=closing,
                assigned_to=assigned_to_id,
                primary_contact_id=primary_contact_id,
                notes=notes,
                last_touch=last_touch,
                relationship_brief=relationship_brief,
                disambiguator=disambiguator
            )
            session.add(prospect)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_prospect(org: str, offering: str) -> None:
    """Delete a prospect."""
    session = get_session()
    try:
        org_obj = session.query(Organization).filter(Organization.name.ilike(org)).first()
        off_obj = session.query(Offering).filter(Offering.name.ilike(offering)).first()

        if org_obj and off_obj:
            prospect = session.query(Prospect).filter_by(
                organization_id=org_obj.id,
                offering_id=off_obj.id
            ).first()
            if prospect:
                session.delete(prospect)
                session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_prospect_field(org: str, offering: str, field: str, value: str) -> None:
    """Update a single field on a prospect. Also auto-updates Last Touch."""
    prospect = get_prospect(org, offering)
    if prospect is None:
        return

    # Normalize field name
    field_normalized = field.lower().replace('_', ' ')

    # Reject next_action
    if field_normalized == 'next action':
        return

    # Normalize urgent: True/False/boolean-string → "Yes" or ""
    if field_normalized == 'urgent':
        value = 'Yes' if str(value).lower() in ('yes', 'true', '1') else ''

    # Enforce single string for assigned_to
    if field_normalized == 'assigned to' and ';' in str(value):
        value = str(value).split(';')[0].strip()

    field_title = next(
        (k for k in PROSPECT_FIELD_ORDER if k.lower() == field_normalized),
        BRIEF_FIELD_MAP.get(field_normalized, field)
    )

    prospect[field_title] = value

    # Auto-update last touch
    if field_normalized not in BRIEF_FIELD_MAP:
        prospect['Last Touch'] = date.today().isoformat()

    write_prospect(org, offering, prospect)

    # Auto-link contact to org when Primary Contact is set
    if field_normalized == 'primary contact' and value:
        ensure_contact_linked(value, org)


# ---------------------------------------------------------------------------
# Pipeline summaries
# ---------------------------------------------------------------------------

def get_fund_summary(offering: str) -> dict:
    """Get pipeline summary for a single offering."""
    prospects = load_prospects(offering)
    config = load_crm_config()
    excluded = set(config['terminal_stages'] + ['0. Not Pursuing'])
    active = [p for p in prospects if p.get('Stage', '') not in excluded]

    total_target = sum(_parse_currency(p.get('Target', '0')) for p in active)

    committed_stages = {'6. Verbal', '7. Legal / DD', '8. Closed'}
    total_committed = sum(
        _parse_currency(p.get('Target', '0'))
        for p in prospects
        if p.get('Stage', '') in committed_stages
    )

    offering_data = get_offering(offering) or {}
    fund_target = _parse_currency(offering_data.get('Target', '0'))

    return {
        'offering': offering,
        'prospect_count': len(active),
        'total_target': total_target,
        'total_target_fmt': _format_currency(total_target),
        'total_committed': total_committed,
        'total_committed_fmt': _format_currency(total_committed),
        'fund_target': fund_target,
        'fund_target_fmt': _format_currency(fund_target),
    }


def get_fund_summary_all() -> list[dict]:
    """Get pipeline summaries for all offerings."""
    return [get_fund_summary(o['name']) for o in load_offerings()]


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------

def load_interactions(org: str = None, offering: str = None, limit: int = None) -> list[dict]:
    """Load interactions, optionally filtered."""
    session = get_session()
    try:
        query = session.query(Interaction).order_by(Interaction.interaction_date.desc())

        if org:
            org_obj = session.query(Organization).filter(Organization.name.ilike(org)).first()
            if org_obj:
                query = query.filter_by(organization_id=org_obj.id)

        if offering:
            off_obj = session.query(Offering).filter(Offering.name.ilike(offering)).first()
            if off_obj:
                query = query.filter_by(offering_id=off_obj.id)

        if limit:
            query = query.limit(limit)

        interactions = query.all()
        result = []

        for i in interactions:
            org_obj = session.query(Organization).filter_by(id=i.organization_id).first()
            off_obj = session.query(Offering).filter_by(id=i.offering_id).first() if i.offering_id else None
            contact = session.query(Contact).filter_by(id=i.contact_id).first() if i.contact_id else None

            result.append({
                'date': i.interaction_date.isoformat(),
                'org': org_obj.name if org_obj else '',
                'type': i.type.value if i.type else '',
                'offering': off_obj.name if off_obj else '',
                'Contact': contact.name if contact else '',
                'Subject': i.subject,
                'Summary': i.summary,
                'Source': i.source.value if i.source else 'manual',
            })

        return result
    finally:
        session.close()


def append_interaction(entry: dict) -> None:
    """Append an interaction entry. Also updates prospect last_touch."""
    session = get_session()
    try:
        org_name = entry.get('org', '')
        org_obj = session.query(Organization).filter(Organization.name.ilike(org_name)).first()
        if not org_obj:
            return

        offering_name = entry.get('offering', '')
        offering_id = None
        if offering_name:
            off_obj = session.query(Offering).filter(Offering.name.ilike(offering_name)).first()
            if off_obj:
                offering_id = off_obj.id

        contact_str = entry.get('Contact', entry.get('contact', ''))
        contact_id = None
        if contact_str:
            contact = session.query(Contact).filter(
                Contact.organization_id == org_obj.id,
                Contact.name.ilike(f'%{contact_str}%')
            ).first()
            if contact:
                contact_id = contact.id

        date_str = entry.get('date', date.today().isoformat())
        try:
            interaction_date = datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            interaction_date = date.today()

        type_str = entry.get('type', 'Note')
        type_enum = InteractionType.Note
        if 'email' in type_str.lower():
            type_enum = InteractionType.Email
        elif 'meeting' in type_str.lower():
            type_enum = InteractionType.Meeting
        elif 'call' in type_str.lower():
            type_enum = InteractionType.Call

        source_str = entry.get('Source', entry.get('source', 'manual'))
        source_enum = InteractionSource.manual
        if 'auto-graph' in source_str.lower():
            source_enum = InteractionSource.auto_graph
        elif 'auto-teams' in source_str.lower():
            source_enum = InteractionSource.auto_teams

        interaction = Interaction(
            organization_id=org_obj.id,
            offering_id=offering_id,
            contact_id=contact_id,
            interaction_date=interaction_date,
            type=type_enum,
            subject=entry.get('Subject', entry.get('subject', '')),
            summary=entry.get('Summary', entry.get('summary', '')),
            source=source_enum,
            source_ref=source_str
        )
        session.add(interaction)
        session.commit()

        # Update last_touch on prospect
        if org_name and offering_name:
            update_prospect_field(org_name, offering_name, 'Last Touch', interaction_date.isoformat())
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Meeting History
# ---------------------------------------------------------------------------

MEETING_HISTORY_PATH = os.path.join(PROJECT_ROOT, 'crm', 'meeting_history.md')


def load_meeting_history(org: str) -> list[dict]:
    """Load meeting history from markdown file (not migrated in Phase I1)."""
    if not os.path.exists(MEETING_HISTORY_PATH):
        return []

    with open(MEETING_HISTORY_PATH, 'r') as f:
        text = f.read()

    in_section = False
    results = []

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith('## '):
            in_section = (stripped[3:].strip().lower() == org.lower())
            continue

        if not in_section or not stripped.startswith('- '):
            continue

        parts = stripped[2:].split(' | ')
        date_m = re.match(r'\*\*([^*]+)\*\*', parts[0].strip())
        date_val = date_m.group(1) if date_m else parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ''
        attendees = parts[2].strip() if len(parts) > 2 else ''
        source_raw = parts[3].strip() if len(parts) > 3 else ''
        notion_url_m = re.search(r'\[Notion\]\(([^)]+)\)', source_raw)
        notion_url = notion_url_m.group(1) if notion_url_m else ''

        results.append({
            'date': date_val,
            'title': title,
            'attendees': attendees,
            'source': source_raw,
            'notion_url': notion_url,
        })

    return results


def add_meeting_entry(org: str, date: str, title: str, attendees: str, source: str, notion_url: str = '') -> None:
    """Append a meeting entry to markdown file (not migrated in Phase I1)."""
    # Deduplicate
    for m in load_meeting_history(org):
        if m['date'] == date and m['title'].lower() == title.lower():
            return

    if notion_url and source == 'calendar':
        source_str = f'calendar + [Notion]({notion_url})'
    elif notion_url:
        source_str = f'[Notion]({notion_url})'
    else:
        source_str = source or 'manual'

    entry_line = f'- **{date}** | {title} | {attendees} | {source_str}'

    if os.path.exists(MEETING_HISTORY_PATH):
        with open(MEETING_HISTORY_PATH, 'r') as f:
            text = f.read()
    else:
        text = '# Meeting History\n'

    lines = text.splitlines()
    section_line = None
    for i, line in enumerate(lines):
        if line.strip() == f'## {org}':
            section_line = i
            break

    if section_line is None:
        if lines and lines[-1].strip():
            lines.append('')
        lines.append(f'## {org}')
        lines.append(entry_line)
    else:
        insert_pos = section_line + 1
        while insert_pos < len(lines) and not lines[insert_pos].startswith('## '):
            insert_pos += 1
        lines.insert(insert_pos, entry_line)

    with open(MEETING_HISTORY_PATH, 'w') as f:
        f.write('\n'.join(lines) + '\n')


# ---------------------------------------------------------------------------
# Email Log
# ---------------------------------------------------------------------------

def load_email_log() -> dict:
    """Load all emails from email_scan_log table."""
    session = get_session()
    try:
        emails = session.query(EmailScanLog).order_by(EmailScanLog.scanned_at.desc()).all()
        return {
            'version': 1,
            'lastScan': emails[0].scanned_at.isoformat() + 'Z' if emails else None,
            'emails': [
                {
                    'messageId': e.message_id,
                    'from': e.from_email,
                    'to': e.to_emails.split(', ') if e.to_emails else [],
                    'subject': e.subject,
                    'timestamp': e.email_date.isoformat() + 'T00:00:00Z' if e.email_date else '',
                    'orgMatch': e.org_name,
                    'snippet': e.snippet,
                    'webLink': e.outlook_url,
                }
                for e in emails
            ]
        }
    finally:
        session.close()


def find_email_by_message_id(message_id: str) -> dict | None:
    """Return email entry from log or None."""
    session = get_session()
    try:
        email = session.query(EmailScanLog).filter_by(message_id=message_id).first()
        if not email:
            return None
        return {
            'messageId': email.message_id,
            'from': email.from_email,
            'to': email.to_emails.split(', ') if email.to_emails else [],
            'subject': email.subject,
            'timestamp': email.email_date.isoformat() + 'T00:00:00Z' if email.email_date else '',
            'orgMatch': email.org_name,
            'snippet': email.snippet,
            'webLink': email.outlook_url,
        }
    finally:
        session.close()


def get_emails_for_org(org_name: str) -> list[dict]:
    """Return all emails matching an org."""
    session = get_session()
    try:
        emails = session.query(EmailScanLog).filter(
            EmailScanLog.org_name.ilike(org_name)
        ).order_by(EmailScanLog.email_date.desc()).all()

        return [
            {
                'messageId': e.message_id,
                'from': e.from_email,
                'to': e.to_emails.split(', ') if e.to_emails else [],
                'subject': e.subject,
                'timestamp': e.email_date.isoformat() + 'T00:00:00Z' if e.email_date else '',
                'orgMatch': e.org_name,
                'snippet': e.snippet,
                'webLink': e.outlook_url,
            }
            for e in emails
        ]
    finally:
        session.close()


def add_emails_to_log(emails: list[dict]) -> int:
    """Append emails to log, deduplicating by messageId."""
    session = get_session()
    try:
        added = 0
        for email in emails:
            mid = email.get('messageId')
            if not mid:
                continue

            existing = session.query(EmailScanLog).filter_by(message_id=mid).first()
            if existing:
                continue

            timestamp = email.get('timestamp', '')
            email_date = None
            if timestamp:
                try:
                    email_date = datetime.fromisoformat(timestamp.rstrip('Z')).date()
                except (ValueError, TypeError):
                    pass

            log_entry = EmailScanLog(
                message_id=mid,
                from_email=email.get('from', ''),
                to_emails=', '.join(email.get('to', [])),
                subject=email.get('subject', ''),
                email_date=email_date,
                org_name=email.get('orgMatch', ''),
                matched=bool(email.get('orgMatch')),
                snippet=email.get('snippet', ''),
                outlook_url=email.get('webLink', '')
            )
            session.add(log_entry)
            added += 1

        session.commit()
        return added
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_org_domains(prospect_only: bool = False) -> dict:
    """Return map of org name -> domain."""
    session = get_session()
    try:
        query = session.query(Organization).filter(Organization.domain != '')

        if prospect_only:
            # Only orgs with active prospects
            prospect_org_ids = session.query(Prospect.organization_id).distinct().all()
            prospect_org_ids = [oid[0] for oid in prospect_org_ids]
            query = query.filter(Organization.id.in_(prospect_org_ids))

        orgs = query.all()
        domains = {}
        for org in orgs:
            if org.name in _SERVICE_PROVIDER_ORGS:
                continue
            domain = org.domain.strip().lstrip('@').lower()
            if domain and domain not in _GENERIC_DOMAINS:
                domains[org.name] = domain

        return domains
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Email enrichment helpers
# ---------------------------------------------------------------------------

def enrich_org_domain(org_name: str, domain: str) -> bool:
    """Add Domain field to an org if it doesn't already have one."""
    if not org_name or not domain:
        return False
    domain = domain.lower().lstrip('@')
    if domain in _GENERIC_DOMAINS or domain in _INTERNAL_DOMAINS:
        return False

    session = get_session()
    try:
        org = session.query(Organization).filter(Organization.name.ilike(org_name)).first()
        if not org:
            return False
        existing_domain = org.domain.strip().lstrip('@').lower()
        if existing_domain:
            return False
        org.domain = f'@{domain}'
        org.updated_at = datetime.now()
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def append_person_email_history(slug: str, date_str: str, subject: str, direction: str) -> None:
    """Phase I1: No-op (person files stay local, not migrated)."""
    pass


def append_org_email_history(org_name: str, date_str: str, subject: str, contact: str, direction: str) -> None:
    """Phase I1: No-op (org email history stays in markdown)."""
    pass


def discover_and_enrich_contact_emails(org_name: str, email_addresses: list[tuple[str, str]]) -> dict:
    """Given a list of (email, display_name), enrich contacts."""
    result = {'domain_added': False, 'emails_enriched': 0, 'details': []}
    if not org_name or not email_addresses:
        return result

    session = get_session()
    try:
        # Try to set org domain
        for email_addr, _ in email_addresses:
            if not email_addr:
                continue
            domain = email_addr.split('@')[-1].lower()
            if domain not in _GENERIC_DOMAINS and domain not in _INTERNAL_DOMAINS:
                if enrich_org_domain(org_name, domain):
                    result['domain_added'] = True
                    result['details'].append(f"Added domain @{domain} to {org_name}")
                break

        # Get org
        org = session.query(Organization).filter(Organization.name.ilike(org_name)).first()
        if not org:
            return result

        org_domain = org.domain.strip().lstrip('@').lower()
        contacts = session.query(Contact).filter_by(organization_id=org.id).all()

        for email_addr, display_name in email_addresses:
            if not email_addr:
                continue
            email_lower = email_addr.lower()
            addr_domain = email_lower.split('@')[-1]

            if addr_domain in _INTERNAL_DOMAINS or addr_domain in _GENERIC_DOMAINS:
                continue

            if org_domain and addr_domain != org_domain:
                continue

            already_has = session.query(Contact).filter(Contact.email.ilike(email_addr)).first()
            if already_has:
                continue

            for contact in contacts:
                if contact.email:
                    continue
                contact_name = contact.name.lower()
                display_lower = display_name.lower().strip()
                if not contact_name or not display_lower:
                    continue

                name_parts = contact_name.split()
                if any(part in display_lower for part in name_parts if len(part) >= 3):
                    contact.email = email_addr
                    contact.updated_at = datetime.now()
                    result['emails_enriched'] += 1
                    result['details'].append(f"Set email {email_addr} on {contact.name}")
                    break

        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Briefs
# ---------------------------------------------------------------------------

def save_brief(brief_type: str, key: str, narrative: str, content_hash: str, at_a_glance: str = '') -> None:
    """Persist an AI-generated brief."""
    session = get_session()
    try:
        brief = session.query(Brief).filter_by(brief_type=brief_type, key=key).first()
        if brief:
            brief.narrative = narrative
            brief.content_hash = content_hash
            if at_a_glance:
                brief.at_a_glance = at_a_glance
            brief.updated_at = datetime.now()
        else:
            brief = Brief(
                brief_type=brief_type,
                key=key,
                narrative=narrative,
                content_hash=content_hash,
                at_a_glance=at_a_glance
            )
            session.add(brief)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def load_saved_brief(brief_type: str, key: str) -> dict | None:
    """Return saved brief or None."""
    session = get_session()
    try:
        brief = session.query(Brief).filter_by(brief_type=brief_type, key=key).first()
        if not brief:
            return None
        return {
            'narrative': brief.narrative,
            'content_hash': brief.content_hash,
            'generated_at': brief.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'at_a_glance': brief.at_a_glance,
        }
    finally:
        session.close()


def load_all_briefs() -> dict:
    """Return all briefs grouped by type."""
    session = get_session()
    try:
        briefs = session.query(Brief).all()
        result = {'prospect': {}, 'person': {}, 'org': {}}
        for b in briefs:
            result.setdefault(b.brief_type, {})[b.key] = {
                'narrative': b.narrative,
                'content_hash': b.content_hash,
                'generated_at': b.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'at_a_glance': b.at_a_glance,
            }
        return result
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Prospect Notes
# ---------------------------------------------------------------------------

def load_prospect_notes(org: str, offering: str) -> list:
    """Load the freeform notes log for a prospect."""
    session = get_session()
    try:
        notes = session.query(ProspectNote).filter(
            ProspectNote.org_name.ilike(org),
            ProspectNote.offering_name.ilike(offering)
        ).order_by(ProspectNote.created_at).all()

        return [
            {
                'date': n.created_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'author': n.author,
                'text': n.text,
            }
            for n in notes
        ]
    finally:
        session.close()


def save_prospect_note(org: str, offering: str, author: str, text: str) -> dict:
    """Append a timestamped note entry."""
    session = get_session()
    try:
        now = datetime.now()
        note = ProspectNote(
            org_name=org,
            offering_name=offering,
            author=author.strip(),
            text=text.strip(),
            created_at=now
        )
        session.add(note)
        session.commit()

        return {
            'date': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'author': author.strip(),
            'text': text.strip(),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Unmatched / Pending
# ---------------------------------------------------------------------------

def load_unmatched() -> list[dict]:
    """Load unmatched emails."""
    session = get_session()
    try:
        unmatched = session.query(UnmatchedEmail).all()
        return [
            {
                'participant_email': u.email,
                'participant_name': u.display_name,
                'subject': u.subject,
                'date': u.date.isoformat() if u.date else '',
            }
            for u in unmatched
        ]
    finally:
        session.close()


def add_unmatched(item: dict) -> None:
    """Add an unmatched email."""
    session = get_session()
    try:
        email = item.get('participant_email', '').lower()
        existing = session.query(UnmatchedEmail).filter(UnmatchedEmail.email.ilike(email)).first()
        if existing:
            return

        date_str = item.get('date', '')
        date_obj = None
        if date_str:
            try:
                date_obj = datetime.fromisoformat(date_str).date()
            except (ValueError, TypeError):
                pass

        unmatched = UnmatchedEmail(
            email=email,
            display_name=item.get('participant_name', ''),
            subject=item.get('subject', ''),
            date=date_obj
        )
        session.add(unmatched)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def remove_unmatched(email: str) -> None:
    """Remove an unmatched email."""
    session = get_session()
    try:
        unmatched = session.query(UnmatchedEmail).filter(UnmatchedEmail.email.ilike(email)).first()
        if unmatched:
            session.delete(unmatched)
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def purge_old_unmatched(days: int = 14) -> None:
    """Remove unmatched emails older than N days."""
    session = get_session()
    try:
        cutoff = (date.today() - timedelta(days=days))
        session.query(UnmatchedEmail).filter(UnmatchedEmail.date < cutoff).delete()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def add_pending_interview(entry: dict) -> None:
    """Add a pending interview."""
    session = get_session()
    try:
        pending = PendingInterview(
            org_name=entry.get('org', ''),
            offering_name=entry.get('offering', ''),
            reason=entry.get('reason', '')
        )
        session.add(pending)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Tasks (from TASKS.md — local file, not migrated)
# ---------------------------------------------------------------------------

def load_tasks_by_org() -> dict[str, list[dict]]:
    """Parse TASKS.md and return open tasks grouped by org name."""
    if not os.path.exists(TASKS_MD_PATH):
        return {}

    with open(TASKS_MD_PATH, 'r') as f:
        text = f.read()

    result = {}
    current_section = None
    task_index = 0

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith('## '):
            current_section = stripped[3:].strip()
            task_index = 0
            continue

        if current_section in ('Personal', 'Done', None):
            continue

        if stripped.startswith('- [ ]') or stripped.startswith('- [x]'):
            if stripped.startswith('- [x]'):
                task_index += 1
                continue

            pri_match = re.search(r'\*\*\[(\w+)\]\*\*', stripped)
            priority = pri_match.group(1) if pri_match else 'Med'

            owner_match = re.search(r'\*\*@([^*]+)\*\*', stripped)
            if owner_match:
                owner = owner_match.group(1).strip()
            else:
                assigned_match = re.search(r'—\s*assigned:(.+)$', stripped)
                owner = assigned_match.group(1).strip() if assigned_match else 'Oscar'

            org_match = re.search(r'\(([^)]+)\)\s*(?:—\s*assigned:[^)]*)?$', stripped)
            if not org_match:
                task_index += 1
                continue

            org_name = org_match.group(1).strip()

            desc = stripped
            desc = re.sub(r'^- \[ \]\s*\*\*\[\w+\]\*\*\s*', '', desc)
            desc = re.sub(r'\*\*@[^*]+\*\*\s*', '', desc)
            desc = re.sub(r'\s*—\s*assigned:.*$', '', desc)
            desc = re.sub(r'\s*\([^)]+\)\s*$', '', desc)
            desc = desc.strip(' —-')

            result.setdefault(org_name, []).append({
                'task': desc,
                'owner': owner,
                'section': current_section,
                'index': task_index,
                'priority': priority,
            })

            task_index += 1

    return result


def get_tasks_for_prospect(org_name: str) -> list[dict]:
    """Scan TASKS.md for tasks tagged [org: org_name]."""
    if not os.path.exists(TASKS_MD_PATH):
        return []

    with open(TASKS_MD_PATH, 'r') as f:
        text = f.read()

    results = []
    current_section = None
    org_lower = org_name.lower()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## '):
            current_section = stripped[3:].strip()
            continue

        if current_section:
            task = _parse_org_tagged_task(line, current_section)
            if task and task['org'].lower() == org_lower:
                results.append({k: v for k, v in task.items() if k != 'org'})

    return results


def _parse_org_tagged_task(line: str, section: str) -> dict | None:
    """Parse a TASKS.md line with [org: ...] tag."""
    stripped = line.strip()
    if not (stripped.startswith('- [ ]') or stripped.startswith('- [x]')):
        return None
    org_m = re.search(r'\[org:\s*([^\]]+)\]', stripped)
    if not org_m:
        return None
    org_name = org_m.group(1).strip()
    status = 'done' if stripped.startswith('- [x]') else 'open'
    pri_m = re.search(r'\*\*\[(\w+)\]\*\*', stripped)
    priority = pri_m.group(1) if pri_m else 'Med'
    owner_m = re.search(r'\[owner:\s*([^\]]+)\]', stripped)
    owner = owner_m.group(1).strip() if owner_m else ''

    text = re.sub(r'^- \[.\]\s*', '', stripped)
    text = re.sub(r'\*\*\[\w+\]\*\*\s*', '', text)
    text = re.sub(r'\[org:\s*[^\]]+\]', '', text)
    text = re.sub(r'\[owner:\s*[^\]]+\]', '', text)
    text = text.strip(' —-').strip()

    return {
        'org': org_name,
        'text': text,
        'owner': owner,
        'priority': priority,
        'status': status,
        'section': section,
        'raw_line': stripped,
    }


def get_all_prospect_tasks() -> list[dict]:
    """Scan TASKS.md for all tasks tagged with any [org: ...] tag."""
    if not os.path.exists(TASKS_MD_PATH):
        return []

    with open(TASKS_MD_PATH, 'r') as f:
        text = f.read()

    results = []
    current_section = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('## '):
            current_section = stripped[3:].strip()
            continue
        if current_section:
            task = _parse_org_tagged_task(line, current_section)
            if task:
                results.append(task)

    return results


def add_prospect_task(org_name: str, text: str, owner: str, priority: str = "Med", section: str = "IR / Fundraising") -> bool:
    """Append a new prospect task to TASKS.md."""
    if not org_name or not text or not owner:
        return False
    if not os.path.exists(TASKS_MD_PATH):
        return False

    new_line = f'- [ ] **[{priority}]** {text} — [org: {org_name}] [owner: {owner}]\n'

    with open(TASKS_MD_PATH, 'r') as f:
        lines = f.readlines()

    target = f'## {section}'
    inserted = False
    for i, ln in enumerate(lines):
        if ln.strip() == target:
            lines.insert(i + 1, new_line)
            inserted = True
            break

    if not inserted:
        lines.append(f'\n## {section}\n')
        lines.append(new_line)

    with open(TASKS_MD_PATH, 'w') as f:
        f.writelines(lines)

    return True


def complete_prospect_task(org_name: str, task_text: str) -> bool:
    """Find open task matching org_name + partial text, mark it done."""
    if not os.path.exists(TASKS_MD_PATH):
        return False

    with open(TASKS_MD_PATH, 'r') as f:
        lines = f.readlines()

    org_lower = org_name.lower()
    text_lower = task_text.lower().strip()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith('- [ ]'):
            continue
        org_m = re.search(r'\[org:\s*([^\]]+)\]', stripped)
        if not org_m or org_m.group(1).strip().lower() != org_lower:
            continue
        if text_lower in stripped.lower():
            lines[i] = line.replace('- [ ]', '- [x]', 1)
            with open(TASKS_MD_PATH, 'w') as f:
                f.writelines(lines)
            return True

    return False


# ---------------------------------------------------------------------------
# Cross-reference (not used in current codebase, but kept for compatibility)
# ---------------------------------------------------------------------------

def get_prospect_full(org: str, offering: str) -> dict | None:
    """Get prospect with org data and contacts."""
    prospect = get_prospect(org, offering)
    if not prospect:
        return None
    org_data = get_organization(org) or {}
    contacts = get_contacts_for_org(org)
    return {**prospect, **{f'org_{k}': v for k, v in org_data.items() if k != 'name'}, 'contacts': contacts}


def resolve_primary_contact(org: str, contact_name: str) -> dict | None:
    """Find a contact by name within an org."""
    for person in get_contacts_for_org(org):
        if person.get('name', '').lower() == contact_name.lower():
            return person
    return None


# ---------------------------------------------------------------------------
# Organization merge (stub implementation for PostgreSQL backend)
# ---------------------------------------------------------------------------

def get_merge_preview(source: str, target: str) -> dict:
    """Preview what will be merged when merging source into target."""
    # TODO: Implement PostgreSQL-backed merge preview
    return {
        'source_org': get_organization(source),
        'target_org': get_organization(target),
        'source_contacts': get_contacts_for_org(source),
        'target_contacts': get_contacts_for_org(target),
        'source_prospects': get_prospects_for_org(source),
        'target_prospects': get_prospects_for_org(target),
        'message': 'Merge preview (PostgreSQL backend)',
    }


def merge_organizations(source: str, target: str) -> dict:
    """Merge source org into target org."""
    # TODO: Implement PostgreSQL-backed organization merge
    # This should:
    # 1. Move all contacts from source to target
    # 2. Move all prospects from source to target (handle conflicts)
    # 3. Move all interactions from source to target
    # 4. Delete source org
    raise NotImplementedError(
        "Organization merge not yet implemented for PostgreSQL backend. "
        "Please manually move contacts/prospects and delete source org."
    )
