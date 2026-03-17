# Skills — Version Control

Git-tracked backups of all custom Cowork skills owned by this repo.

## How it works

- **Live copy** (what Cowork reads): `~/.skills/skills/<skill-name>/SKILL.md`
- **Repo copy** (version-controlled backup): `docs/skills/<skill-name>/SKILL.md`

The live path is controlled by Cowork — never rename or restructure it.
The repo copy is what gives you git history, diffs, and rollback.

## Skills tracked here

| Skill | Command | Status |
|-------|---------|--------|
| crm-update | `/crm-update` | Active |
| email-scan | `/email-scan` | Active |
| email | `/email` | Active |
| bdr-update | `/bdr-update` | Not yet created |
| arec-pitch-deck | `/arec-pitch-deck` | Not yet created |

## After editing a skill

After editing a skill in Cowork (via skill-creator) or manually, copy the updated live file into the repo and commit:

```bash
# Example: after editing crm-update
cp ~/.skills/skills/crm-update/SKILL.md \
   ~/Dropbox/projects/arec-crm/docs/skills/crm-update/SKILL.md
cd ~/Dropbox/projects/arec-crm
git add docs/skills/crm-update/SKILL.md
git commit -m "skills: update crm-update"
git push
```

Repeat for any skill by substituting the skill name.

## To roll back a skill

Copy the desired version from git history back to the live location:

```bash
# Roll back crm-update to the previous commit's version
git show HEAD~1:docs/skills/crm-update/SKILL.md > \
   ~/.skills/skills/crm-update/SKILL.md
```

Or roll back to a specific commit:

```bash
git show <commit-hash>:docs/skills/crm-update/SKILL.md > \
   ~/.skills/skills/crm-update/SKILL.md
```

## Live skills path note

The live path Cowork reads is `~/.skills/skills/` (not `~/Documents/Claude/Skills/skills/` as some older docs may say). Confirm with `ls ~/.skills/skills/` if in doubt.
