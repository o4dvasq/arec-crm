"""
One-time migration script: Parse markdown CRM files and insert into PostgreSQL.

Reads from crm/*.md and memory/people/*.md, writes to Postgres.
Idempotent: can be run multiple times (upserts based on unique constraints).
"""

import os
import sys
import json
import hashlib
from datetime import datetime

# Add app/ to path
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(APP_DIR, '.env.azure'))

from models import (
    Organization, Offering, Contact, Prospect, Interaction, EmailScanLog,
    Brief, ProspectNote, UnmatchedEmail, PendingInterview, User,
    InteractionType, InteractionSource, UrgencyLevel, ClosingOption
)
from db import init_db, session_scope
from sources.crm_reader import (
    load_organizations, load_offerings, load_prospects, load_contacts_index,
    load_person, load_interactions, load_email_log, load_all_briefs,
    load_prospect_notes, load_unmatched, load_pending_interviews,
    _parse_currency, get_team_member_email
)

PROJECT_ROOT = os.path.dirname(APP_DIR)
CRM_ROOT = os.path.join(PROJECT_ROOT, 'crm')

# Stage remapping per spec §3.3
STAGE_REMAP = {
    '2. Qualified': '2. Cold',
    '3. Presentation': '3. Outreach',
}

# Org type normalization per spec §3.2
def normalize_org_type(org_type: str) -> str:
    """Normalize 'HNWI/FO' → 'HNWI / FO' (add space)."""
    if org_type == 'HNWI/FO':
        return 'HNWI / FO'
    return org_type


def migrate_organizations(session):
    """Migrate organizations from organizations.md."""
    print("\nMigrating organizations...")
    orgs_data = load_organizations()
    count = 0

    for org_data in orgs_data:
        name = org_data['name']
        org_type = normalize_org_type(org_data.get('Type', ''))
        domain = org_data.get('Domain', '').strip()
        notes = org_data.get('Notes', '')

        # Upsert
        org = session.query(Organization).filter_by(name=name).first()
        if org:
            org.type = org_type
            org.domain = domain
            org.notes = notes
            org.updated_at = datetime.now()
        else:
            org = Organization(
                name=name,
                type=org_type,
                domain=domain,
                notes=notes
            )
            session.add(org)
        count += 1

    session.flush()
    print(f"✓ Migrated {count} organizations")
    return count


def migrate_offerings(session):
    """Migrate offerings from offerings.md."""
    print("\nMigrating offerings...")
    offerings_data = load_offerings()
    count = 0

    for off_data in offerings_data:
        name = off_data['name']
        target_str = off_data.get('Target', '0')
        hard_cap_str = off_data.get('Hard Cap', '0')

        # Convert to cents
        target_cents = int(_parse_currency(target_str) * 100)
        hard_cap_cents = int(_parse_currency(hard_cap_str) * 100) if hard_cap_str else None

        # Upsert
        offering = session.query(Offering).filter_by(name=name).first()
        if offering:
            offering.target = target_cents
            offering.hard_cap = hard_cap_cents
            offering.updated_at = datetime.now()
        else:
            offering = Offering(
                name=name,
                target=target_cents,
                hard_cap=hard_cap_cents
            )
            session.add(offering)
        count += 1

    session.flush()
    print(f"✓ Migrated {count} offerings")
    return count


def migrate_contacts(session):
    """Migrate contacts from contacts_index.md and memory/people/*.md."""
    print("\nMigrating contacts...")
    index = load_contacts_index()
    count = 0

    for org_name, slugs in index.items():
        # Find org (case-insensitive, handle disambiguator)
        base_org = org_name.split(' (')[0].strip()  # "UTIMCO (Jared)" → "UTIMCO"
        org = session.query(Organization).filter(Organization.name.ilike(base_org)).first()
        if not org:
            print(f"  ⚠ Org not found for contacts: {org_name} (base: {base_org})")
            continue

        for slug in slugs:
            person = load_person(slug)
            if not person:
                print(f"  ⚠ Person file not found: {slug}")
                continue

            name = person.get('name', '')
            if not name:
                print(f"  ⚠ Person has no name: {slug}")
                continue

            title = person.get('role', '')
            email = person.get('email', '')
            phone = person.get('phone', '')

            # Upsert contact
            contact = session.query(Contact).filter_by(
                name=name, organization_id=org.id
            ).first()

            if contact:
                contact.title = title
                contact.email = email
                contact.phone = phone
                contact.updated_at = datetime.now()
            else:
                contact = Contact(
                    name=name,
                    organization_id=org.id,
                    title=title,
                    email=email,
                    phone=phone
                )
                session.add(contact)
            count += 1

    session.flush()
    print(f"✓ Migrated {count} contacts")
    return count


def migrate_prospects(session):
    """Migrate prospects from prospects.md."""
    print("\nMigrating prospects...")
    prospects_data = load_prospects()
    count = 0
    skipped = 0

    for pros_data in prospects_data:
        org_name = pros_data['org']
        offering_name = pros_data['offering']
        disambiguator = pros_data.get('disambiguator')

        # Find org and offering
        org = session.query(Organization).filter(Organization.name.ilike(org_name)).first()
        if not org:
            print(f"  ⚠ Org not found: {org_name}")
            skipped += 1
            continue

        offering = session.query(Offering).filter(Offering.name.ilike(offering_name)).first()
        if not offering:
            print(f"  ⚠ Offering not found: {offering_name}")
            skipped += 1
            continue

        # Parse fields
        stage_raw = pros_data.get('Stage', '1. Prospect')
        stage = STAGE_REMAP.get(stage_raw, stage_raw)

        target_str = pros_data.get('Target', '0')
        target_cents = int(_parse_currency(target_str) * 100)

        committed_str = pros_data.get('Committed', '0')
        committed_cents = int(_parse_currency(committed_str) * 100)

        # Urgency enum
        urgent_raw = pros_data.get('Urgent', '').strip()
        urgency = None
        if urgent_raw:
            if urgent_raw.lower() in ('yes', 'high'):
                urgency = UrgencyLevel.High
            elif urgent_raw.lower() == 'med':
                urgency = UrgencyLevel.Med
            elif urgent_raw.lower() == 'low':
                urgency = UrgencyLevel.Low

        # Closing enum
        closing_raw = pros_data.get('Closing', '').strip()
        closing = None
        if closing_raw:
            if '1st' in closing_raw.lower():
                closing = ClosingOption.First
            elif '2nd' in closing_raw.lower():
                closing = ClosingOption.Second
            elif 'final' in closing_raw.lower():
                closing = ClosingOption.Final

        # Assigned to (take first name from semicolon-separated list)
        assigned_to_str = pros_data.get('Assigned To', '').strip()
        assigned_to_id = None
        if assigned_to_str:
            first_name = assigned_to_str.split(';')[0].strip()
            # Look up user by name (case-insensitive partial match)
            user = session.query(User).filter(
                User.display_name.ilike(f'%{first_name}%')
            ).first()
            if user:
                assigned_to_id = user.id

        # Primary contact
        primary_contact_str = pros_data.get('Primary Contact', '').strip()
        primary_contact_id = None
        if primary_contact_str:
            # Take first contact name from comma/semicolon-separated list
            first_contact_name = primary_contact_str.replace(';', ',').split(',')[0].strip()
            contact = session.query(Contact).filter(
                Contact.organization_id == org.id,
                Contact.name.ilike(f'%{first_contact_name}%')
            ).first()
            if contact:
                primary_contact_id = contact.id

        notes = pros_data.get('Notes', '')
        last_touch_str = pros_data.get('Last Touch', '')
        last_touch = None
        if last_touch_str:
            try:
                last_touch = datetime.fromisoformat(last_touch_str).date()
            except (ValueError, TypeError):
                pass

        relationship_brief = pros_data.get('Relationship Brief', '')

        # Upsert prospect
        prospect = session.query(Prospect).filter_by(
            organization_id=org.id,
            offering_id=offering.id,
            disambiguator=disambiguator
        ).first()

        if prospect:
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
            prospect = Prospect(
                organization_id=org.id,
                offering_id=offering.id,
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
        count += 1

    session.flush()
    print(f"✓ Migrated {count} prospects ({skipped} skipped due to missing org/offering)")
    return count


def migrate_interactions(session):
    """Migrate interactions from interactions.md."""
    print("\nMigrating interactions...")
    interactions_data = load_interactions()
    count = 0

    for int_data in interactions_data:
        org_name = int_data.get('org', '')
        offering_name = int_data.get('offering', '')
        date_str = int_data.get('date', '')
        type_str = int_data.get('type', 'Note')
        subject = int_data.get('Subject', '')
        summary = int_data.get('Summary', '')
        contact_str = int_data.get('Contact', '')
        source_str = int_data.get('Source', 'manual')

        # Find org
        org = session.query(Organization).filter(Organization.name.ilike(org_name)).first()
        if not org:
            continue

        # Find offering
        offering_id = None
        if offering_name:
            offering = session.query(Offering).filter(Offering.name.ilike(offering_name)).first()
            if offering:
                offering_id = offering.id

        # Find contact
        contact_id = None
        if contact_str:
            contact = session.query(Contact).filter(
                Contact.organization_id == org.id,
                Contact.name.ilike(f'%{contact_str}%')
            ).first()
            if contact:
                contact_id = contact.id

        # Parse date
        try:
            interaction_date = datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            interaction_date = datetime.now().date()

        # Map type
        type_enum = InteractionType.Note
        type_lower = type_str.lower()
        if 'email' in type_lower:
            type_enum = InteractionType.Email
        elif 'meeting' in type_lower:
            type_enum = InteractionType.Meeting
        elif 'call' in type_lower:
            type_enum = InteractionType.Call
        elif 'document sent' in type_lower:
            type_enum = InteractionType.DocumentSent
        elif 'document received' in type_lower:
            type_enum = InteractionType.DocumentReceived

        # Map source
        source_enum = InteractionSource.manual
        if 'auto-graph' in source_str.lower():
            source_enum = InteractionSource.auto_graph
        elif 'auto-teams' in source_str.lower():
            source_enum = InteractionSource.auto_teams
        elif 'forwarded' in source_str.lower():
            source_enum = InteractionSource.forwarded_email

        # Create interaction (no dedup — interactions can have duplicates)
        interaction = Interaction(
            organization_id=org.id,
            offering_id=offering_id,
            contact_id=contact_id,
            interaction_date=interaction_date,
            type=type_enum,
            subject=subject,
            summary=summary,
            source=source_enum,
            source_ref=source_str,
            team_members=[]
        )
        session.add(interaction)
        count += 1

    session.flush()
    print(f"✓ Migrated {count} interactions")
    return count


def migrate_email_log(session):
    """Migrate email_log.json to email_scan_log table."""
    print("\nMigrating email log...")
    log_data = load_email_log()
    emails = log_data.get('emails', [])
    count = 0

    for email in emails:
        message_id = email.get('messageId', '')
        if not message_id:
            continue

        from_email = email.get('from', '')
        to_emails = ', '.join(email.get('to', []))
        subject = email.get('subject', '')
        timestamp = email.get('timestamp', '')
        org_match = email.get('orgMatch', '')
        snippet = email.get('snippet', '')
        outlook_url = email.get('webLink', '')

        # Parse date
        email_date = None
        if timestamp:
            try:
                email_date = datetime.fromisoformat(timestamp.rstrip('Z')).date()
            except (ValueError, TypeError):
                pass

        matched = bool(org_match)

        # Upsert
        log_entry = session.query(EmailScanLog).filter_by(message_id=message_id).first()
        if not log_entry:
            log_entry = EmailScanLog(
                message_id=message_id,
                from_email=from_email,
                to_emails=to_emails,
                subject=subject,
                email_date=email_date,
                org_name=org_match,
                matched=matched,
                snippet=snippet,
                outlook_url=outlook_url
            )
            session.add(log_entry)
            count += 1

    session.flush()
    print(f"✓ Migrated {count} email log entries")
    return count


def migrate_briefs(session):
    """Migrate briefs.json to briefs table."""
    print("\nMigrating briefs...")
    briefs_data = load_all_briefs()
    count = 0

    for brief_type, entries in briefs_data.items():
        for key, brief in entries.items():
            narrative = brief.get('narrative', '')
            at_a_glance = brief.get('at_a_glance', '')
            content_hash = brief.get('content_hash', '')

            # Upsert
            brief_obj = session.query(Brief).filter_by(brief_type=brief_type, key=key).first()
            if brief_obj:
                brief_obj.narrative = narrative
                brief_obj.at_a_glance = at_a_glance
                brief_obj.content_hash = content_hash
                brief_obj.updated_at = datetime.now()
            else:
                brief_obj = Brief(
                    brief_type=brief_type,
                    key=key,
                    narrative=narrative,
                    at_a_glance=at_a_glance,
                    content_hash=content_hash
                )
                session.add(brief_obj)
            count += 1

    session.flush()
    print(f"✓ Migrated {count} briefs")
    return count


def migrate_prospect_notes(session):
    """Migrate prospect_notes.json to prospect_notes table."""
    print("\nMigrating prospect notes...")
    count = 0

    notes_path = os.path.join(CRM_ROOT, 'prospect_notes.json')
    if not os.path.exists(notes_path):
        print("  (No prospect_notes.json found)")
        return 0

    with open(notes_path, 'r') as f:
        notes_data = json.load(f)

    for key, notes_list in notes_data.items():
        # key format: "OrgName::OfferingName"
        parts = key.split('::', 1)
        if len(parts) != 2:
            continue
        org_name, offering_name = parts

        for note in notes_list:
            author = note.get('author', '')
            text = note.get('text', '')
            date_str = note.get('date', '')

            # Parse created_at
            created_at = datetime.now()
            if date_str:
                try:
                    created_at = datetime.fromisoformat(date_str.rstrip('Z'))
                except (ValueError, TypeError):
                    pass

            note_obj = ProspectNote(
                org_name=org_name,
                offering_name=offering_name,
                author=author,
                text=text,
                created_at=created_at
            )
            session.add(note_obj)
            count += 1

    session.flush()
    print(f"✓ Migrated {count} prospect notes")
    return count


def migrate_unmatched_emails(session):
    """Migrate unmatched_review.json to unmatched_emails table."""
    print("\nMigrating unmatched emails...")
    unmatched = load_unmatched()
    count = 0

    for item in unmatched:
        email = item.get('participant_email', '')
        display_name = item.get('participant_name', '')
        subject = item.get('subject', '')
        date_str = item.get('date', '')

        # Parse date
        date_obj = None
        if date_str:
            try:
                date_obj = datetime.fromisoformat(date_str).date()
            except (ValueError, TypeError):
                pass

        # Upsert by email
        unmatched_obj = session.query(UnmatchedEmail).filter_by(email=email).first()
        if not unmatched_obj:
            unmatched_obj = UnmatchedEmail(
                email=email,
                display_name=display_name,
                subject=subject,
                date=date_obj
            )
            session.add(unmatched_obj)
            count += 1

    session.flush()
    print(f"✓ Migrated {count} unmatched emails")
    return count


def migrate_pending_interviews(session):
    """Migrate pending_interviews.json to pending_interviews table."""
    print("\nMigrating pending interviews...")
    pending = load_pending_interviews()
    count = 0

    for item in pending:
        org_name = item.get('org', '')
        offering_name = item.get('offering', '')
        reason = item.get('reason', '')

        pending_obj = PendingInterview(
            org_name=org_name,
            offering_name=offering_name,
            reason=reason
        )
        session.add(pending_obj)
        count += 1

    session.flush()
    print(f"✓ Migrated {count} pending interviews")
    return count


def generate_migration_report(counts):
    """Print summary report."""
    print("\n" + "=" * 50)
    print("MIGRATION SUMMARY")
    print("=" * 50)
    for key, value in counts.items():
        print(f"  {key}: {value}")
    print("=" * 50)
    print("\n✓ Migration complete!")


def main():
    """Run all migration steps."""
    print("AREC CRM Data Migration: Markdown → PostgreSQL")
    print("=" * 50)

    try:
        init_db()
        counts = {}

        with session_scope() as session:
            counts['Organizations'] = migrate_organizations(session)
            counts['Offerings'] = migrate_offerings(session)
            counts['Contacts'] = migrate_contacts(session)
            counts['Prospects'] = migrate_prospects(session)
            counts['Interactions'] = migrate_interactions(session)
            counts['Email Log Entries'] = migrate_email_log(session)
            counts['Briefs'] = migrate_briefs(session)
            counts['Prospect Notes'] = migrate_prospect_notes(session)
            counts['Unmatched Emails'] = migrate_unmatched_emails(session)
            counts['Pending Interviews'] = migrate_pending_interviews(session)

        generate_migration_report(counts)

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
