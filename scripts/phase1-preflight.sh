#!/bin/bash
# Phase 1 Pre-Flight Check
# Run this BEFORE the migration to verify everything is safe to move.
# Compatible with macOS default bash (3.x).
# Usage: bash phase1-preflight.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

pass()  { echo -e "  ${GREEN}✓${NC} $1"; PASS=$((PASS+1)); }
fail()  { echo -e "  ${RED}✗${NC} $1"; FAIL=$((FAIL+1)); }
warn()  { echo -e "  ${YELLOW}!${NC} $1"; WARN=$((WARN+1)); }

NAMES=( "arec-crm" "arec-lending-intelligence" "sf-stairways" "photography" )
PATHS=( "$HOME/Dropbox/Tech/ClaudeProductivity" "$HOME/Desktop/arec-lending-intelligence" "$HOME/Documents/Stairs" "$HOME/Documents/Photography" )

echo ""
echo "═══════════════════════════════════════════════"
echo "  Phase 1 Pre-Flight Check"
echo "═══════════════════════════════════════════════"
echo ""

echo "1. Checking source directories exist..."
for i in 0 1 2 3; do
  name="${NAMES[$i]}"
  path="${PATHS[$i]}"
  if [ -d "$path" ]; then
    pass "$name → $path"
  else
    fail "$name → $path NOT FOUND"
  fi
done

echo ""
echo "2. Checking git status (nothing uncommitted)..."
for i in 0 1 2 3; do
  name="${NAMES[$i]}"
  path="${PATHS[$i]}"
  if [ -d "$path/.git" ]; then
    cd "$path"
    STATUS=$(git status --porcelain 2>/dev/null)
    if [ -z "$STATUS" ]; then
      pass "$name — clean working tree"
    else
      fail "$name — has uncommitted changes:"
      echo "$STATUS" | head -10 | sed 's/^/       /'
    fi
  else
    warn "$name — no .git directory (will need git init after move)"
  fi
done

echo ""
echo "3. Checking git remotes..."
for i in 0 1 2 3; do
  name="${NAMES[$i]}"
  path="${PATHS[$i]}"
  if [ -d "$path/.git" ]; then
    cd "$path"
    REMOTE=$(git remote -v 2>/dev/null | head -1)
    if [ -n "$REMOTE" ]; then
      pass "$name — $REMOTE"
    else
      warn "$name — no remote configured"
    fi
  fi
done

echo ""
echo "4. Checking all repos are pushed..."
for i in 0 1 2 3; do
  name="${NAMES[$i]}"
  path="${PATHS[$i]}"
  if [ -d "$path/.git" ]; then
    cd "$path"
    AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "unknown")
    if [ "$AHEAD" = "0" ]; then
      pass "$name — up to date with remote"
    elif [ "$AHEAD" = "unknown" ]; then
      warn "$name — no upstream tracking branch (check manually)"
    else
      fail "$name — $AHEAD commit(s) ahead of remote, push first!"
    fi
  fi
done

echo ""
echo "5. Checking target directory..."
if [ -d "$HOME/Dropbox/projects" ]; then
  warn "~/Dropbox/projects/ already exists"
  ls -la "$HOME/Dropbox/projects/" | sed 's/^/       /'
else
  pass "~/Dropbox/projects/ does not exist yet (will be created)"
fi

echo ""
echo "6. Checking Dropbox path..."
if [ -d "$HOME/Dropbox" ]; then
  pass "~/Dropbox/ exists (classic path)"
elif [ -d "$HOME/Library/CloudStorage/Dropbox" ]; then
  fail "Dropbox is at ~/Library/CloudStorage/Dropbox/ — scripts need path update!"
else
  fail "Cannot find Dropbox directory"
fi

echo ""
echo "═══════════════════════════════════════════════"
echo -e "  Results: ${GREEN}$PASS passed${NC}  ${RED}$FAIL failed${NC}  ${YELLOW}$WARN warnings${NC}"
echo "═══════════════════════════════════════════════"
echo ""

if [ $FAIL -gt 0 ]; then
  echo -e "${RED}Fix failures before running the migration script.${NC}"
  exit 1
else
  echo -e "${GREEN}Pre-flight passed. Safe to run phase1-migrate.sh${NC}"
fi
