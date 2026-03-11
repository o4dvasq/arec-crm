## Project Locations
- All projects live in ~/Dropbox/projects/[name]/
- .git directories are Dropbox-ignored (xattr) on every project
- Source files sync via Dropbox between machines
- Git state syncs via GitHub (commit + push before switching machines)
- NEVER put .git in a Dropbox-synced location without the ignore attribute
- New projects: use bootstrap.sh which auto-ignores .git

## Multi-Machine Workflow
- Before leaving a machine: /switch-machine (commits and pushes)
- After arriving at other machine: git pull in the project directory
- One-time setup per project per machine: init git, add remote, fetch, checkout, xattr ignore .git
