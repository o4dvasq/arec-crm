## Project Locations
- All projects live in ~/Dropbox/projects/[name]/
- .git directories are Dropbox-ignored (xattr) on every project
- Source files sync via Dropbox between machines
- Git state syncs via GitHub (commit + push before switching machines)
- NEVER put .git in a Dropbox-synced location without the ignore attribute
- New projects: use bootstrap.sh which auto-ignores .git

## Multi-Machine Workflow
- Before leaving a machine: `/leave-machine` (stages, commits WIP, pushes)
- After arriving at other machine: `/start-coding` (pulls latest, checks branch, shows project state)
- `/switch-machine` is deprecated — use `/leave-machine` + `/start-coding` instead
- One-time setup per project per machine: init git, add remote, fetch, checkout, xattr ignore .git
- After cloning or setting up a new machine, run `bash scripts/install-hooks.sh` to install git guardrails
