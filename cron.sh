#!/bin/bash
cd /opt/SAS
git pull

/home/agentbot/.local/bin/codex exec --model gpt-6-terra -c model_reasoning_effort=medium --dangerously-bypass-approvals-and-sandbox "$(cat /opt/SAS/cron)" 2>&1 | tail -10 >> /opt/SAS/cron.log

cd /opt/SAS
git add . && git commit -m 'logs' && git push
