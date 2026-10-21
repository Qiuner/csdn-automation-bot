#!/bin/bash
set -euo pipefail
cd /home/fmops/csdn-automation-bot
until=${1:?Pass the original timezone-aware deadline}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
report="/app/web/Chrome/visit-random-${stamp}.json"
log="/app/web/Chrome/visit-random-${stamp}.log"
sudo -n docker compose -p csdn-automation-bot -f deploy/compose.yaml exec -d bot \
  bash -c 'umask 077; printf "\n" | timeout --signal=TERM --kill-after=30s 86520s python -u web/visit_schedule.py "$1" --interval 60 --jitter 10 --until "$4" --output "$2" --execute > "$3" 2>&1' \
  bash 'https://blog.csdn.net/qq_61654952/article/details/166116044' "$report" "$log" "$until"
printf 'REPORT=%s\nLOG=%s\n' "$report" "$log"
