#!/bin/bash
# Phase 2 — Set up git on Machine B
# Run this on your second Mac AFTER Dropbox has synced the source files.
# The .git folders won't be there (Dropbox-ignored), so we re-init each repo.
# Compatible with macOS default bash (3.x).
# Usage: bash phase2-machine-b.sh

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "═══════════════════════════════════════════════"
echo "  Phase 2: Machine B Git Setup"
echo "═══════════════════════════════════════════════"
echo ""

PROJECTS=( "arec-crm" "arec-lending-intelligence" "sf-stairways" "photography" )
REMOTES=( "git@github.com:o4dvasq/arec-crm.git" "git@github.com:o4dvasq/arec-lending-intelligence.git" "git@github.com:o4dvasq/sf-stairways.git" "git@github.com:o4dvasq/photography.git" )

echo "Checking Dropbox has synced project directories..."
ALL_PRESENT=true
for project in "${PROJECTS[@]}"; do
  if [ -d ~/Dropbox/projects/$project ]; then
    echo -e "  ${GREEN}✓${NC} $project present"
  else
    echo -e "  ${RED}✗${NC} $project NOT FOUND — wait for Dropbox to finish syncing"
    ALL_PRESENT=false
  fi
done

if [ "$ALL_PRESENT" = false ]; then
  echo ""
  echo -e "${RED}Some directories missing. Wait for Dropbox sync and re-run.${NC}"
  exit 1
fi

echo ""

for i in 0 1 2 3; do
  project="${PROJECTS[$i]}"
  REMOTE="${REMOTES[$i]}"
  DIR=~/Dropbox/projects/$project

  echo "Setting up $project..."

  if [ -d "$DIR/.git" ]; then
    echo -e "  ${YELLOW}!${NC} .git already exists — skipping (already initialized)"
    echo ""
    continue
  fi

  cd "$DIR"
  git init
  git remote add origin "$REMOTE"
  git fetch origin
  git checkout main
  xattr -w com.dropbox.ignored 1 .git
  echo -e "  ${GREEN}✓${NC} initialized, checked out main, .git Dropbox-ignored"
  echo ""
done

echo "Ignoring generated directories..."
for DIR in __pycache__ .venv venv; do
  TARGET=~/Dropbox/projects/arec-lending-intelligence/$DIR
  if [ -d "$TARGET" ]; then
    xattr -w com.dropbox.ignored 1 "$TARGET"
    echo -e "  ${GREEN}✓${NC} arec-lending-intelligence/$DIR ignored"
  fi
done
find ~/Dropbox/projects -maxdepth 2 -type d -name "node_modules" -exec xattr -w com.dropbox.ignored 1 {} \; 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════"
echo -e "  ${GREEN}Phase 2 complete!${NC}"
echo "  All projects have local git repos pointing to GitHub."
echo "  Dropbox syncs source files. GitHub syncs git state."
echo "═══════════════════════════════════════════════"
