#!/bin/bash

commit_and_push_repo() {
  local repo_path="$1"
  local commit_message="$2"

  cd "$repo_path" || exit 1
  if [ -n "$(git status --short)" ]; then
    git add .
    git commit -m "$commit_message"
    git push
  fi
}

cd /opt/SAS/sas-api
git pull
cd /opt/SAS/sas-ui
git pull
cd /opt/SAS
git pull

echo -e "\n\n[$(date)] - Running $1" >> /opt/SAS/logs/cron.log
/home/agentbot/.local/bin/codex exec resume --last --model gpt-5.4 --dangerously-bypass-approvals-and-sandbox "$(cat "$1")" 2>&1 | tail -20 >> /opt/SAS/logs/cron.log
echo "[$(date)] - Done" >> /opt/SAS/logs/cron.log

commit_and_push_repo /opt/SAS/sas-api "cron updates"
commit_and_push_repo /opt/SAS/sas-ui "cron updates"
commit_and_push_repo /opt/SAS "logs"
