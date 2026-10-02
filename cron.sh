#!/bin/bash
cd /opt/SAS
git pull

/home/agentbot/.local/bin/codex exec --model gpt-6.1-sol -c model_reasoning_effort=medium --dangerously-bypass-approvals-and-sandbox "$(cat /opt/SAS/cron)" 2>&1 | tail -10 >> /opt/SAS/cron.log
# gpt-6-luna    $0.10 / $0.50	Very good for the price
# gpt-5.6-luna	$0.20 / $1.20	Good, but 6 Luna makes it less attractive
# gpt-6.1-sol	  $2 / $10	Excellent
# gpt-6-sol	    $2 / $10	Excellent, but superseded by 6.1
# gpt-5.6-terra	$2 / $12	Very good
# gpt-5.6-sol	  $4 / $20	Excellent, but poor value now
# gpt-6-astra	  $10 / $50	Best capability, massive overkill for routine runs


cd /opt/SAS
git add . && git commit -m 'logs' && git push
