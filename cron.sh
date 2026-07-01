#!/bin/bash
cd /opt/SAS || exit 1
/home/agentbot/.local/bin/codex exec --model gpt-5.4 --dangerously-bypass-approvals-and-sandbox "$(cat "$1")" 2>&1 | tail -20 >> /opt/SAS/logs/cron.log
