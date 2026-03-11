#!/bin/bash
# Phase 1 Migration — Move projects to ~/Dropbox/projects/
# Run AFTER phase1-preflight.sh passes.
# Usage: bash phase1-migrate.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "═══════════════════════════════════════════════"
echo "  Phase 1: Project Consolidation"
echo "═══════════════════════════════════════════════"
echo ""

echo "Step 1: Creating target directory..."
mkdir -p ~/Dropbox/projects
echo -e "  ${GREEN}✓${NC} ~/Dropbox/projects/ created"

echo ""
echo "Step 2: Moving projects..."

mv ~/Dropbox/Tech/ClaudeProductivity ~/Dropbox/projects/arec-crm
echo -e "  ${GREEN}✓${NC} arec-crm moved"

mv ~/Desktop/arec-lending-intelligence ~/Dropbox/projects/arec-lending-intelligence
echo -e "  ${GREEN}✓${NC} arec-lending-intelligence moved"

mv ~/Documents/Stairs ~/Dropbox/projects/sf-stairways
echo -e "  ${GREEN}✓${NC} sf-stairways moved"

mv ~/Documents/Photography ~/Dropbox/projects/photography
echo -e "  ${GREEN}✓${NC} photography moved"

echo ""
echo "Step 3: Verifying git remotes survived the move..."
for project in arec-crm arec-lending-intelligence sf-stairways photography; do
  DIR=~/Dropbox/projects/$project
  if [ -d "$DIR/.git" ]; then
    REMOTE=$(cd "$DIR" && git remote -v 2>/dev/null | grep fetch | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} $project → $REMOTE"
  else
    echo -e "  ${YELLOW}!${NC} $project — no .git (will init below)"
  fi
done

echo ""
echo "Step 4: Marking .git directories as Dropbox-ignored..."
for project in arec-lending-intelligence sf-stairways photography; do
  GIT_DIR=~/Dropbox/projects/$project/.git
  if [ -d "$GIT_DIR" ]; then
    xattr -w com.dropbox.ignored 1 "$GIT_DIR"
    echo -e "  ${GREEN}✓${NC} $project/.git ignored"
  fi
done

if [ -d ~/Dropbox/projects/arec-crm/.git ]; then
  xattr -w com.dropbox.ignored 1 ~/Dropbox/projects/arec-crm/.git
  echo -e "  ${GREEN}✓${NC} arec-crm/.git ignored"
else
  echo -e "  ${YELLOW}!${NC} arec-crm has no .git — initializing..."
  cd ~/Dropbox/projects/arec-crm
  git init
  git remote add origin git@github.com:o4dvasq/arec-crm.git
  # NOTE: Create this repo on GitHub first if it doesn't exist:
  # gh repo create o4dvasq/arec-crm --private
  git add .
  git commit -m "Initial commit — consolidating to ~/Dropbox/projects"
  git push -u origin main
  xattr -w com.dropbox.ignored 1 .git
  echo -e "  ${GREEN}✓${NC} arec-crm initialized, pushed, .git ignored"
fi

echo ""
echo "Step 5: Ignoring generated directories..."
for DIR in __pycache__ .venv venv; do
  TARGET=~/Dropbox/projects/arec-lending-intelligence/$DIR
  if [ -d "$TARGET" ]; then
    xattr -w com.dropbox.ignored 1 "$TARGET"
    echo -e "  ${GREEN}✓${NC} arec-lending-intelligence/$DIR ignored"
  fi
done

find ~/Dropbox/projects -maxdepth 2 -type d -name "node_modules" -exec xattr -w com.dropbox.ignored 1 {} \; 2>/dev/null && echo -e "  ${GREEN}✓${NC} node_modules directories ignored" || true

echo ""
echo "Step 6: Final verification..."
echo ""
echo "  Directory structure:"
ls -1d ~/Dropbox/projects/*/ 2>/dev/null | sed 's|.*/projects/|  ~/Dropbox/projects/|'

echo ""
echo "  Dropbox ignore status (.git dirs):"
for project in arec-crm arec-lending-intelligence sf-stairways photography; do
  GIT_DIR=~/Dropbox/projects/$project/.git
  if [ -d "$GIT_DIR" ]; then
    IGNORED=$(xattr -p com.dropbox.ignored "$GIT_DIR" 2>/dev/null || echo "NOT SET")
    if [ "$IGNORED" = "1" ]; then
      echo -e "  ${GREEN}✓${NC} $project/.git — ignored"
    else
      echo -e "  ${YELLOW}!${NC} $project/.git — NOT ignored (run xattr manually)"
    fi
  fi
done

echo ""
echo "═══════════════════════════════════════════════"
echo -e "  ${GREEN}Phase 1 complete!${NC}"
echo ""
echo "  Next steps:"
echo "    1. Check Finder — .git folders should show gray minus icon"
echo "    2. Source files should show green checkmarks"
echo "    3. Wait for Dropbox to finish syncing"
echo "    4. On Machine B: run phase2-machine-b.sh"
echo "═══════════════════════════════════════════════"
