"""
SQLAlchemy ORM models for arec-crm PostgreSQL schema.

Corresponds to the schema defined in SPEC_phase-I1-database-auth-webapp.md § 4.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, BigInteger, Date, TIMESTAMP,
    ForeignKey, Enum, UniqueConstraint, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UrgencyLevel(enum.Enum):
    High = "High"
    Med = "Med"
    Low = "Low"


class ClosingOption(enum.Enum):
    First = "1st"
    Second = "2nd"
    Final = "Final"


class InteractionType(enum.Enum):
    Email = "Email"
    Meeting = "Meeting"
    Call = "Call"
    Note = "Note"
    DocumentSent = "Document Sent"
    DocumentReceived = "Document Received"


class InteractionSource(enum.Enum):
    manual = "manual"
    auto_graph = "auto-graph"
    auto_teams = "auto-teams"
    forwarded_email = "forwarded-email"


class BriefingScope(enum.Enum):
    executive = "executive"
    full = "full"
    standard = "standard"
    minimal = "minimal"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    entra_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='user')
    is_active = Column(Boolean, default=True)
    briefing_enabled = Column(Boolean, default=True)
    briefing_scope = Column(Enum(BriefingScope), default=BriefingScope.standard)
    created_at = Column(TIMESTAMP, default=datetime.now)
    last_login = Column(TIMESTAMP, nullable=True)
    graph_consent_granted = Column(Boolean, default=False)
    graph_consent_date = Column(TIMESTAMP, nullable=True)

    # Relationships
    prospects_assigned = relationship('Prospect', foreign_keys='Prospect.assigned_to', back_populates='assignee')
    interactions_created = relationship('Interaction', foreign_keys='Interaction.created_by', back_populates='creator')


class Offering(Base):
    __tablename__ = 'offerings'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    target = Column(BigInteger, nullable=True)
    hard_cap = Column(BigInteger, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.now)
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    prospects = relationship('Prospect', back_populates='offering')


class Organization(Base):
    __tablename__ = 'organizations'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    type = Column(String(100), nullable=False)
    domain = Column(String(255), default='')
    notes = Column(Text, default='')
    created_at = Column(TIMESTAMP, default=datetime.now)
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    contacts = relationship('Contact', back_populates='organization', cascade='all, delete-orphan')
    prospects = relationship('Prospect', back_populates='organization', cascade='all, delete-orphan')
    interactions = relationship('Interaction', back_populates='organization', cascade='all, delete-orphan')


class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), default='')
    email = Column(String(255), default='')
    phone = Column(String(255), default='')
    notes = Column(Text, default='')
    created_at = Column(TIMESTAMP, default=datetime.now)
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        UniqueConstraint('name', 'organization_id', name='uq_contact_name_org'),
        Index('idx_contacts_org', 'organization_id'),
        Index('idx_contacts_email', 'email'),
    )

    # Relationships
    organization = relationship('Organization', back_populates='contacts')
    prospects = relationship('Prospect', foreign_keys='Prospect.primary_contact_id', back_populates='primary_contact')
    interactions = relationship('Interaction', back_populates='contact')


class PipelineStage(Base):
    __tablename__ = 'pipeline_stages'

    id = Column(Integer, primary_key=True)
    number = Column(Integer, unique=True, nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    is_terminal = Column(Boolean, default=False)
    sort_order = Column(Integer, nullable=False)


class Prospect(Base):
    __tablename__ = 'prospects'

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    offering_id = Column(Integer, ForeignKey('offerings.id', ondelete='CASCADE'), nullable=False)
    stage = Column(String(50), nullable=False, default='1. Prospect')
    target = Column(BigInteger, default=0)
    committed = Column(BigInteger, default=0)
    primary_contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    closing = Column(Enum(ClosingOption), nullable=True)
    urgency = Column(Enum(UrgencyLevel), nullable=True)
    assigned_to = Column(Integer, ForeignKey('users.id'), nullable=True)
    next_action = Column(Text, default='')
    notes = Column(Text, default='')
    last_touch = Column(Date, nullable=True)
    relationship_brief = Column(Text, default='')
    disambiguator = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.now)
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    updated_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        UniqueConstraint('organization_id', 'offering_id', 'disambiguator', name='uq_prospect_org_off_disambig'),
        Index('idx_prospects_offering', 'offering_id'),
        Index('idx_prospects_org', 'organization_id'),
        Index('idx_prospects_stage', 'stage'),
    )

    # Relationships
    organization = relationship('Organization', back_populates='prospects')
    offering = relationship('Offering', back_populates='prospects')
    primary_contact = relationship('Contact', foreign_keys=[primary_contact_id], back_populates='prospects')
    assignee = relationship('User', foreign_keys=[assigned_to], back_populates='prospects_assigned')


class Interaction(Base):
    __tablename__ = 'interactions'

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    offering_id = Column(Integer, ForeignKey('offerings.id'), nullable=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'), nullable=True)
    interaction_date = Column(Date, nullable=False)
    type = Column(Enum(InteractionType), nullable=False)
    subject = Column(String(500), default='')
    summary = Column(Text, default='')
    source = Column(Enum(InteractionSource), default=InteractionSource.manual)
    source_ref = Column(String(500), default='')
    team_members = Column(JSON, default=list)
    created_at = Column(TIMESTAMP, default=datetime.now)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        Index('idx_interactions_org', 'organization_id'),
        Index('idx_interactions_date', 'interaction_date'),
    )

    # Relationships
    organization = relationship('Organization', back_populates='interactions')
    offering = relationship('Offering')
    contact = relationship('Contact', back_populates='interactions')
    creator = relationship('User', foreign_keys=[created_by], back_populates='interactions_created')


class EmailScanLog(Base):
    __tablename__ = 'email_scan_log'

    id = Column(Integer, primary_key=True)
    message_id = Column(String(500), unique=True, nullable=False)
    from_email = Column(String(255), default='')
    to_emails = Column(Text, default='')
    subject = Column(String(500), default='')
    email_date = Column(Date, nullable=True)
    org_name = Column(String(255), default='')
    matched = Column(Boolean, default=False)
    snippet = Column(Text, default='')
    outlook_url = Column(Text, default='')
    scanned_at = Column(TIMESTAMP, default=datetime.now)
    scanned_by = Column(Integer, ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        Index('idx_email_scan_msg', 'message_id'),
        Index('idx_email_scan_org', 'org_name'),
    )


class Brief(Base):
    __tablename__ = 'briefs'

    id = Column(Integer, primary_key=True)
    brief_type = Column(String(50), nullable=False)
    key = Column(String(255), nullable=False)
    narrative = Column(Text, default='')
    at_a_glance = Column(Text, default='')
    content_hash = Column(String(64), default='')
    created_at = Column(TIMESTAMP, default=datetime.now)
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('brief_type', 'key', name='uq_brief_type_key'),
        Index('idx_briefs_type_key', 'brief_type', 'key'),
    )


class ProspectNote(Base):
    __tablename__ = 'prospect_notes'

    id = Column(Integer, primary_key=True)
    org_name = Column(String(255), nullable=False)
    offering_name = Column(String(255), nullable=False)
    author = Column(String(255), default='')
    text = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.now)


class UnmatchedEmail(Base):
    __tablename__ = 'unmatched_emails'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), default='')
    subject = Column(String(500), default='')
    date = Column(Date, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.now)


class PendingInterview(Base):
    __tablename__ = 'pending_interviews'

    id = Column(Integer, primary_key=True)
    org_name = Column(String(255), nullable=False)
    offering_name = Column(String(255), default='')
    reason = Column(Text, default='')
    created_at = Column(TIMESTAMP, default=datetime.now)


class ProspectTask(Base):
    __tablename__ = 'prospect_tasks'

    id = Column(Integer, primary_key=True)
    org_name = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    owner = Column(String(255), default='')
    priority = Column(String(20), default='Med')
    status = Column(String(20), default='open')
    created_at = Column(TIMESTAMP, default=datetime.now)
    completed_at = Column(TIMESTAMP, nullable=True)
