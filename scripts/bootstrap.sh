#!/bin/bash
# Bootstrap a new AREC project in ~/Dropbox/projects/
# Usage: ./bootstrap.sh project-name

set -e

if [ -z "$1" ]; then
  echo "Usage: ./bootstrap.sh project-name"
  exit 1
fi

PROJECT_NAME=$1
BASE=~/Dropbox/projects
TEMPLATES=~/Dropbox/projects/claude-workflow-system

if [ ! -d "$TEMPLATES" ]; then
  echo "Error: claude-workflow-system not found at $TEMPLATES"
  echo "Place your workflow templates there first."
  exit 1
fi

mkdir -p "$BASE/$PROJECT_NAME/docs/specs"

for FILE in 01_CLAUDE_md_TEMPLATE.md 03_PROJECT_STATE_TEMPLATE.md 05_DECISIONS_TEMPLATE.md; do
  if [ -f "$TEMPLATES/$FILE" ]; then
    case $FILE in
      01_*) cp "$TEMPLATES/$FILE" "$BASE/$PROJECT_NAME/CLAUDE.md" ;;
      03_*) cp "$TEMPLATES/$FILE" "$BASE/$PROJECT_NAME/docs/PROJECT_STATE.md" ;;
      05_*) cp "$TEMPLATES/$FILE" "$BASE/$PROJECT_NAME/docs/DECISIONS.md" ;;
    esac
  fi
done

touch "$BASE/$PROJECT_NAME/docs/ARCHITECTURE.md"

cd "$BASE/$PROJECT_NAME"
git init
git add .
git commit -m "Bootstrap with workflow system"
xattr -w com.dropbox.ignored 1 .git

echo ""
echo "Project created at $BASE/$PROJECT_NAME"
echo ".git marked as Dropbox-ignored"
echo ""
echo "Next steps:"
echo "  1. Create GitHub repo: gh repo create o4dvasq/$PROJECT_NAME --private"
echo "  2. Push:"
echo "     cd $BASE/$PROJECT_NAME"
echo "     git remote add origin git@github.com:o4dvasq/$PROJECT_NAME.git"
echo "     git push -u origin main"
echo "  3. On Machine B after Dropbox syncs:"
echo "     cd $BASE/$PROJECT_NAME"
echo "     git init && git remote add origin git@github.com:o4dvasq/$PROJECT_NAME.git"
echo "     git fetch origin && git checkout main"
echo "     xattr -w com.dropbox.ignored 1 .git"
