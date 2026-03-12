#!/bin/bash
HOOK_DIR="$(git rev-parse --show-toplevel)/.git/hooks"
cat > "$HOOK_DIR/pre-push" << 'HOOK'
#!/bin/bash
while read local_ref local_sha remote_ref remote_sha; do
  if [[ "$remote_ref" == *"deprecated-markdown"* ]]; then
    echo ""
    echo "BLOCKED: You are pushing to 'deprecated-markdown'."
    echo "This branch contains stale markdown-based code."
    echo "All work should go to 'azure-migration'."
    echo ""
    exit 1
  fi
done
exit 0
HOOK
chmod +x "$HOOK_DIR/pre-push"
echo "Pre-push hook installed at $HOOK_DIR/pre-push"
