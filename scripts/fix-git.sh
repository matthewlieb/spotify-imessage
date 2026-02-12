#!/bin/bash
# Fix corrupted or inconsistent git state for spotify-imessage.
# Run from repo root: ./scripts/fix-git.sh

set -e
cd "$(git rev-parse --show-toplevel)"

echo "=== Fixing Git repo ==="
echo ""

echo "1. Removing stale lock and backup files..."
rm -f .git/index.lock .git/"index 3.lock" .git/gc.log .git/gc.log.lock .git/gc.pid 2>/dev/null || true
rm -f .git/"index 2" .git/"index 3" .git/"index 4" 2>/dev/null || true

echo "2. Removing invalid refs and logs (names with spaces)..."
rm -f ".git/refs/remotes/origin/matt 2" ".git/refs/remotes/origin/matt 3" 2>/dev/null || true
rm -f ".git/logs/refs/remotes/origin/matt 3" ".git/logs/refs/heads/develop 2" ".git/logs/HEAD 2" ".git/ORIG_HEAD 2" 2>/dev/null || true
rm -f .git/gc.log 2>/dev/null || true
# If 'matt 2' keeps coming back, delete the branch on GitHub:
# Repo → Branches → find "matt 2" → Delete.

echo "3. Pointing main at origin/main..."
git update-ref refs/heads/main refs/remotes/origin/main 2>/dev/null || true

echo "4. Resetting index and working tree to origin/main..."
echo "   (If this hangs for more than ~30 seconds, press Ctrl+C and run the reclone steps below.)"
if ! git reset --hard origin/main 2>&1; then
  RECLONE=1
fi
if [ "${RECLONE:-0}" = "1" ]; then
  echo ""
  echo "   Reset failed or was cancelled. To get a clean repo without hanging:"
  echo ""
  echo "   cd .."
  echo "   git clone https://github.com/matthewlieb/spotify-imessage.git spotify-imessage-fresh"
  echo "   cd spotify-imessage-fresh"
  echo ""
  echo "   (Copy any uncommitted files you need from the old folder, then use the new one.)"
  exit 1
fi

echo ""
echo "Done. Checking status..."
git status
