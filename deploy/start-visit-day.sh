#!/bin/bash
set -euo pipefail
cd /home/fmops/csdn-automation-bot
stamp=$(date -u +%Y%m%dT%H%M%SZ)
report="/app/web/Chrome/visit-day-${stamp}.json"
log="/app/web/Chrome/visit-day-${stamp}.log"
# Detached exec is independent of SSH. Existing login is checked by the script.
sudo -n docker compose -p csdn-automation-bot -f deploy/compose.yaml exec -d bot \
  bash -c 'umask 077; printf "\n" | timeout --signal=TERM --kill-after=30s 86520s python -u web/visit_schedule.py "$1" --interval 180 --hours 24 --output "$2" --execute > "$3" 2>&1' \
  bash 'https://blog.csdn.net/qq_61654952/article/details/166116044' "$report" "$log"
printf 'REPORT=%s\nLOG=%s\n' "$report" "$log"
