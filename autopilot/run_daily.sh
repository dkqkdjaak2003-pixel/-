#!/usr/bin/env bash
# cron example (매일 10:07, 19:07 실행 / 매일 23:37 성과 수집):
#   7 10,19 * * * /path/to/repo/autopilot/run_daily.sh run
#   37 23 * * *   /path/to/repo/autopilot/run_daily.sh report
#   @reboot       /path/to/repo/autopilot/run_daily.sh telegram   # 텔레그램 봇 상시 실행
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f autopilot/.env ] && set -a && . autopilot/.env && set +a
exec python3 autopilot/autopilot.py "${1:-run}"
