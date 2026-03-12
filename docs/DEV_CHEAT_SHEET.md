# Dev System Cheat Sheet

## Three Tools, One System

| Tool | Best For |
|---|---|
| **Desktop Chat** | Design, planning, specs |
| **Claude Code** | Implementation, git, deploys |
| **Cowork** | Coding + file ops + docs + debugging + automation |

## The Spec Loop (Desktop → Code)

1. Desktop: design the feature
2. Desktop: "generate the spec for [feature]" → save as docs/specs/SPEC_[name].md
3. Code: `/code-start [feature]` → build it
4. Code: `/feedback-loop` → update project docs
5. Desktop: "Read docs/PROJECT_STATE.md" → resume

## Cowork Coding (When Spec Overhead Isn't Worth It)

Mount the project folder. Design and build in one conversation. When done, ask Cowork to update docs/PROJECT_STATE.md and append to docs/DECISIONS.md.

## arec-crm: Branch & Deploy Rules

| Rule | Detail |
|---|---|
| **Active branch** | `azure-migration` — ALL work happens here |
| **Never touch** | `deprecated-markdown` — stale markdown-based code, do not modify (pre-push hook blocks it) |
| **Backend** | PostgreSQL only via `crm_db.py`. No markdown files, no `crm_reader.py` |
| **Push = deploy** | Push to `azure-migration` → GitHub Actions runs 99 tests → auto-deploys to Azure |
| **Production URL** | https://arec-crm-app.azurewebsites.net/crm |

## arec-crm: Daily Workflow

```
git checkout azure-migration
# make changes
python3 -m pytest app/tests/ -v --tb=short
git add [files] && git commit -m "description"
git push origin azure-migration
# CI runs tests → deploys automatically
```

## Slash Commands (Claude Code)

| Command | What |
|---|---|
| `/code-start [feature]` | Load spec, confirm plan |
| `/bug-fix [description]` | Diagnose before fixing |
| `/refactor [target]` | Propose approach first |
| `/feedback-loop` | Update all project docs |
| `/health-check` | Check context mid-session |
| `/leave-machine` | Stage, commit WIP, push — run when done on this machine |
| `/start-coding` | Pull latest, show status, summarize project state — run when sitting down |

## Desktop Chat Shortcuts (no slash needed)

| You Say | What Happens |
|---|---|
| "Read docs/PROJECT_STATE.md" | Resume a project |
| "Generate the spec for [feature]" | Full spec output |
| "Wrap up this design" | Same as above |

## Switching Machines

**Leaving:** `/leave-machine` — stages everything, commits WIP, pushes to GitHub
**Arriving:** `/start-coding` — pulls latest, checks branch, shows project state and any in-progress work

Manual equivalent if slash commands aren't available:

```
git add . && git commit -m "WIP: leaving machine" && git push origin azure-migration
git checkout azure-migration && git pull origin azure-migration
```

## New Project

```
~/Dropbox/projects/claude-workflow-system/bootstrap.sh [name]
gh repo create o4dvasq/[name] --private
cd ~/Dropbox/projects/[name]
git remote add origin git@github.com:o4dvasq/[name].git
git push -u origin main
```

## Git Essentials

```
git status                    # what changed
git checkout azure-migration  # switch to working branch
git add . && git commit -m "" # stage + commit
git push origin azure-migration # send to GitHub (triggers deploy)
git pull origin azure-migration # get from GitHub
git log --oneline -10         # recent history
```

## The Five Project Files

| File | Updates | Rule |
|---|---|---|
| CLAUDE.md | Edit in place | Under 80 lines, no history |
| PROJECT_STATE.md | Overwrite each session | Current state only |
| DECISIONS.md | Append only | Never overwrite |
| ARCHITECTURE.md | Edit when structure changes | On demand |
| SPEC_[feature].md | New file per feature | One feature per spec |

## Where Instructions Live

| Tool | Source |
|---|---|
| Claude Code | ~/.claude/CLAUDE.md (global) + project/CLAUDE.md |
| Desktop Chat | Preferences → Custom Instructions |
| Cowork | Mounted folder's CLAUDE.md only |

## Slash Commands Location

Canonical: `~/Dropbox/projects/claude-workflow-system/commands/`
Symlinked: `~/.claude/commands/` → above (auto-syncs via Dropbox)

## arec-crm: Azure Infrastructure

| Resource | Value |
|---|---|
| App Service | `arec-crm-app` (Linux, Python 3.12, B1, centralus) |
| PostgreSQL | `arec-crm-db` (Flexible Server, B1ms, centralus) |
| Key Vault | `kv-arec-crm` |
| CI/CD | `.github/workflows/azure-deploy.yml` |

## arec-crm: Key Files

| File | What |
|---|---|
| `app/sources/crm_db.py` | PostgreSQL data layer (single source of truth) |
| `app/delivery/crm_blueprint.py` | CRM routes + brief synthesis |
| `app/delivery/dashboard.py` | Flask app factory |
| `app/models.py` | SQLAlchemy ORM (14 tables) |
| `app/auth/entra_auth.py` | Entra ID SSO |
| `app/tests/conftest.py` | Test fixtures (SQLite in-memory) |

## Safety Rules

- .git MUST be xattr-ignored in every Dropbox project
- Recreated .git → re-run: `xattr -w com.dropbox.ignored 1 .git`
- Also ignore: __pycache__, .venv, venv, node_modules
- Every project needs a .gitignore
- Always push to GitHub — Dropbox is NOT version control
- **arec-crm**: `main` has been renamed to `deprecated-markdown`. A pre-push hook blocks pushes to it. If you clone fresh or the hook is missing, run `bash scripts/install-hooks.sh`. Never import `crm_reader.py`. Always run tests before pushing.
