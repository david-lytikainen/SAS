#!/bin/bash
cd /opt/SAS
git pull

/home/agentbot/.local/bin/codex exec resume --last --model gpt-5.6-terra -c model_reasoning_effort=medium --dangerously-bypass-approvals-and-sandbox "$(cat
  /opt/SAS/cron)" 2>&1 | tail -10 >> /opt/SAS/logs/cron.log
echo -e "Done  $(date)\n\n" >> /opt/SAS/logs/cron.log

cd /opt/SAS
git add . && git commit -m 'logs' && git push
