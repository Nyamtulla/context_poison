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
CMD="${1:-status}"

rm -rf "$WORK" && git clone --quiet "$MIRROR" "$WORK" || exit 1

changed() {
    diff -rq --exclude=.git "$WORK" "$REPO/latex" 2>/dev/null
}

case "$CMD" in
  status|pull)
      d="$(changed)"
      if [ -z "$d" ]; then echo "in sync; nothing to do"; exit 0; fi
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
      ;;
  push)
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
      git push -q origin HEAD:main && echo "pushed to the mirror (fast-forward)"
      ;;
  *) echo "usage: $0 {pull|push|status}"; exit 2;;
esac
