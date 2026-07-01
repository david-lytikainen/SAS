#!/bin/bash
cd /opt/SAS || exit 1
codex exec --model gpt-5.4 --sandbox workspace-write --ask-for-approval never "$(cat "$1")" >> /opt/SAS/logs/cron.log 2>&1
