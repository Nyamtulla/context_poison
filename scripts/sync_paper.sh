#!/bin/bash
# Sync latex/ with the Overleaf mirror, without git subtree.
#
#   scripts/sync_paper.sh pull    # see what Overleaf changed, and apply it
#   scripts/sync_paper.sh push    # send latex/ to the mirror
#   scripts/sync_paper.sh status  # compare, change nothing
#
# Why not `git subtree`: the history rewrite that purged the source PDFs
# removed the "git-subtree-dir" marker commit that `git subtree pull` looks
# for, so it fails with "'latex' was never added" and every push after a
# co-author edit needed --force. Forcing a shared branch to move is a bad
# default, and it is avoidable: the mirror is a content copy of latex/, not a
# projection of our history, so a plain clone-copy-commit-push is both simpler
# and safe. Each side keeps its own history and neither rewrites the other's.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
MIRROR="git@github.com:Nyamtulla/context_poison_paper.git"
WORK=/tmp/paper_mirror
STATE="$REPO/.paper_mirror_sync"
CMD="${1:-status}"

rm -rf "$WORK" && git clone --quiet "$MIRROR" "$WORK" || exit 1
HEAD_NOW="$(cd "$WORK" && git rev-parse HEAD)"
SEEN="$(cat "$STATE" 2>/dev/null || echo none)"

# Has the mirror moved since we last pulled or pushed? `push` overwrites the
# mirror wholesale, so a co-author commit we have not integrated is destroyed
# silently. Two Overleaf commits were lost that way before this check existed;
# comparing file contents did not catch it, because a clobbered co-author edit
# looks exactly like one of our own pending edits.
behind() { [ "$SEEN" != "$HEAD_NOW" ]; }

changed() {
    diff -rq --exclude=.git "$WORK" "$REPO/latex" 2>/dev/null
}

case "$CMD" in
  status|pull)
      if behind; then
          echo "the mirror has commits we have not integrated:"
          (cd "$WORK" && git log --oneline "$SEEN..HEAD" 2>/dev/null \
              | sed 's/^/  /') || echo "  (no recorded sync point yet)"
          echo
      fi
      d="$(changed)"
      if [ -z "$d" ]; then
          [ "$CMD" = pull ] && echo "$HEAD_NOW" > "$STATE"
          echo "in sync; nothing to do"; exit 0
      fi
      echo "differences (mirror vs latex/):"; echo "$d" | sed 's/^/  /'
      [ "$CMD" = status ] && exit 0
      echo
      echo "applying the mirror's version of each differing file into latex/"
      echo "REVIEW THE DIFF BEFORE COMMITTING: git diff latex/"
      ( cd "$WORK" && find . -path ./.git -prune -o -type f -print ) \
        | sed 's|^\./||' | while read -r f; do
            if ! cmp -s "$WORK/$f" "$REPO/latex/$f" 2>/dev/null; then
                mkdir -p "$(dirname "$REPO/latex/$f")"
                cp "$WORK/$f" "$REPO/latex/$f"
                echo "  <- $f"
            fi
        done
      echo "$HEAD_NOW" > "$STATE"
      ;;
  push)
      if behind; then
          echo "REFUSING TO PUSH: the mirror has moved since we last synced."
          echo "  mirror HEAD : $HEAD_NOW"
          echo "  last synced : $SEEN"
          echo
          (cd "$WORK" && git log --oneline "$SEEN..HEAD" 2>/dev/null \
              | sed 's/^/  /') || true
          echo
          echo "Those commits are co-author edits. Pushing now would delete"
          echo "them. Commit your work, run '$0 pull', review 'git diff latex/',"
          echo "reapply anything the pull reverted, then push."
          exit 1
      fi
      # copy latex/ over the clone, keeping the clone's .git
      ( cd "$WORK" && find . -path ./.git -prune -o -type f -print ) \
        | sed 's|^\./||' | while read -r f; do
            [ -f "$REPO/latex/$f" ] || { rm -f "$WORK/$f"; echo "  deleted $f"; }
        done
      cp -r "$REPO"/latex/. "$WORK"/
      cd "$WORK" || exit 1
      if git diff --quiet && git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
          echo "mirror already matches latex/; nothing to push"; exit 0
      fi
      git add -A
      git commit -q -m "${2:-Sync from context_sok}"
      if git push -q origin HEAD:main; then
          git rev-parse HEAD > "$STATE"
          echo "pushed to the mirror (fast-forward)"
      else
          exit 1
      fi
      ;;
  *) echo "usage: $0 {pull|push|status}"; exit 2;;
esac
