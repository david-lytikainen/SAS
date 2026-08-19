#!/bin/bash
cd /opt/SAS
git pull

echo -e "\n\n$1  $(date)" >> /opt/SAS/logs/cron.log
/home/agentbot/.local/bin/codex exec resume --last --model gpt-5.4 --dangerously-bypass-approvals-and-sandbox "$(cat "$1")" 2>&1 | tail -10 >> /opt/SAS/logs/cron.log
echo "Done  $(date)" >> /opt/SAS/logs/cron.log

cd /opt/SAS
changed_paths=$(git status --porcelain | awk '{print $2}')
if [ -z "$changed_paths" ]; then
  exit 0
fi

non_log_changes=$(printf "%s\n" "$changed_paths" | grep -v '^logs/cron\.log$' || true)
if [ -n "$non_log_changes" ]; then
  exit 0
fi

git add logs/cron.log && git commit -m 'logs' && git push
