#!/bin/bash
cd /opt/SAS/sas-api
git pull
cd /opt/SAS/sas-ui
git pull
cd /opt/SAS
git pull

echo -e "\n\n[$(date)] - Running $1" >> /opt/SAS/logs/cron.log
/home/agentbot/.local/bin/codex exec resume --last --model gpt-5.4 --dangerously-bypass-approvals-and-sandbox "$(cat "$1")" 2>&1 | tail -20 >> /opt/SAS/logs/cron.log
echo "[$(date)] - Done" >> /opt/SAS/logs/cron.log

cd /opt/SAS
