#!/bin/bash
cd /opt/SAS
git pull

#echo -e "\n\n$1  $(date)" >> /opt/SAS/logs/cron.log
#/home/agentbot/.local/bin/codex exec resume --last --model gpt-5.4 --dangerously-bypass-approvals-and-sandbox "$(cat "$1")" 2>&1 | tail -10 >> /opt/SAS/logs/cron.log
#echo "Done  $(date)" >> /opt/SAS/logs/cron.log

cd /opt/SAS
#git add . && git commit -m 'logs' && git push
