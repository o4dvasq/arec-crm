SPEC: vCard Contact Sync (Two-Way)
Project: arec-crm
Date: 2026-03-16
Status: BACKLOG — needs design pass before implementation

---

## 1. Objective

Enable two-way contact synchronization between the CRM and Outlook via vCard (.vcf) files. Team members should be able to import Outlook contacts into the CRM to enrich existing records or create new contacts, and export CRM contacts as vCards for use in Outlook or other systems.

## 2. High-Level Features

### Import (Outlook → CRM)
- Upload a .vcf file (single or multi-contact) exported from Outlook
- Parse vCard fields: name, email, phone, organization, title, address, notes
- Match against existing CRM contacts by email or name+org
- If match found: enrich existing contact with any new fields (phone, title, address, etc.)
- If no match: create new contact file in `contacts/` with parsed data, prompt for org assignment
- Support bulk import from Outlook "Export Contacts" (multi-vCard)

### Export (CRM → Outlook)
- Add a "Download vCard" button on each contact's detail page in the CRM dashboard
- Generate a .vcf file from the contact's CRM record (name, org, email, phone, role)
- Standard vCard 3.0 format for broad compatibility

## 3. Open Questions (to resolve before implementation)
- Conflict resolution: what happens when vCard has different data than CRM for the same field?
- Should import be a dashboard feature, a CLI command, or a Cowork skill?
- Should export include org-level metadata (e.g., pipeline stage) in vCard notes?
- Batch export: download all contacts for an org as a single multi-vCard?
- Direct Outlook API integration vs. file-based import/export?

## 4. Dependencies
- vCard parsing library (e.g., Python `vobject`)
- CRM dashboard contact detail page (exists)
- `create_person_file()` and `enrich_person_email()` in `crm_reader.py` (exist)
