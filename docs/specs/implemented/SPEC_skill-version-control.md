SPEC: Skill Version Control | Project: arec-crm + overwatch | Date: 2026-03-17 | Status: Ready for implementation

---

## 1. Objective

Git-track all custom Cowork skills in the same repos as the code and data they serve, giving Oscar full version history, diff, and rollback capability — the same rigor applied to app code and markdown data files.

---

## 2. Scope

- arec-crm repo: crm-update, email-scan, email, bdr-update, arec-pitch-deck
- overwatch repo: overwatch-update
- Does NOT cover platform-bundled skills (docx, pdf, pptx, xlsx, schedule, skill-creator) — those are maintained by Anthropic, not Oscar.

---

## 3. Business Rules

- Skills live on disk at `~/Documents/Claude/Skills/skills/<skill-name>/SKILL.md` (the authoritative live copy read by Cowork).
- The repo copy at `docs/skills/<skill-name>/SKILL.md` is the version-controlled backup.
- After any skill edit (via skill-creator or manual), the updated SKILL.md must be committed to the appropriate repo.
- To roll back a skill: copy the desired version from git history back to the live location.
- Skill ownership:
  - arec-crm owns: crm-update, email-scan, email, bdr-update, arec-pitch-deck
  - overwatch owns: overwatch-update
- email-scan is tracked in arec-crm (primary) only, even though it's used from both contexts.

---

## 4. Data Model / Schema Changes

New directory structure:

```
arec-crm/
  docs/
    skills/
      crm-update/
        SKILL.md
      email-scan/
        SKILL.md
      email/
        SKILL.md
      bdr-update/
        SKILL.md
      arec-pitch-deck/
        SKILL.md
      README.md       ← explains the sync/restore workflow

overwatch/
  docs/
    skills/
      overwatch-update/
        SKILL.md
      README.md
```

No changes to any app code, markdown data, or existing directory structure.

---

## 5. UI / Interface

None. No application changes.

---

## 6. Integration Points

Live skill path (read by Cowork):
```
~/Documents/Claude/Skills/skills/<skill-name>/SKILL.md
```

Repo path (version-controlled):
```
~/Dropbox/projects/arec-crm/docs/skills/<skill-name>/SKILL.md
~/Dropbox/projects/overwatch/docs/skills/<skill-name>/SKILL.md
```

Sync commands (documented in each README.md):

```bash
# After editing a skill — copy live → repo and commit:
cp ~/Documents/Claude/Skills/skills/crm-update/SKILL.md \
   ~/Dropbox/projects/arec-crm/docs/skills/crm-update/SKILL.md
cd ~/Dropbox/projects/arec-crm && git add docs/skills/ && git commit -m "skills: update crm-update"
```

```bash
# To roll back a skill to a prior git version:
git show HEAD~1:docs/skills/crm-update/SKILL.md > \
   ~/Documents/Claude/Skills/skills/crm-update/SKILL.md
```

---

## 7. Constraints

- Do NOT rename or restructure the live Claude Skills directory — Cowork resolves skills by folder name and that path is controlled by the app.
- The repo copy is a backup/history store only. The live path is always what Cowork reads.
- Claude Code can read the live Skills directory at `~/Documents/Claude/Skills/skills/` and copy files from it; use that to do the initial population of `docs/skills/`.

---

## 8. Acceptance Criteria

- [ ] `docs/skills/` directory exists in arec-crm with 5 SKILL.md files, content matching live versions
- [ ] `docs/skills/` directory exists in overwatch with 1 SKILL.md file, content matching live version
- [ ] Each repo's `docs/skills/README.md` explains the sync/restore workflow
- [ ] All files committed to main with a descriptive commit message
- [ ] `git log docs/skills/` shows at least one commit with the correct files
- [ ] `git show HEAD:docs/skills/crm-update/SKILL.md` returns the full skill content
- [ ] feedback loop prompt has been run

---

## 9. Files Likely Touched

**arec-crm:**
```
docs/skills/crm-update/SKILL.md          (new)
docs/skills/email-scan/SKILL.md          (new)
docs/skills/email/SKILL.md               (new)
docs/skills/bdr-update/SKILL.md          (new)
docs/skills/arec-pitch-deck/SKILL.md     (new)
docs/skills/README.md                    (new)
```

**overwatch:**
```
docs/skills/overwatch-update/SKILL.md    (new)
docs/skills/README.md                    (new)
```
