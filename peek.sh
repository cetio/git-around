#!/bin/bash
# Dry-run grep for repos touched by git-around script
# Usage: ./peek.sh [path-to-git-around-log-or-output]
# You may want to use piping...

LOGFILE="${1:-git-around.log}"

if [[ ! -f "$LOGFILE" ]]; then
  echo "Log file not found: $LOGFILE"
  exit 1
fi

grep -oE '([a-zA-Z0-9._-]+/){1,2}' "$LOGFILE" | sort -u
