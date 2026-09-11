## Dedicated Scheduler Setup

This keeps scheduled jobs and queued email sending out of the normal web workers.

### What this does

- runs the `sas-api` scheduler in its own process
- handles:
  - next-morning event auto-complete
  - nightly reminder emails
  - queued email delivery like password reset, registration confirmation, waitlist notices, and reminders

Use the same app env vars as the normal API service, including:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `MAIL_SERVER`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `CLIENT_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `CORS_ORIGINS`

### Required database step

Run this SQL before starting the scheduler worker:

```bash
psql "$DATABASE_URL" -f sas-api/sql/20260704_add_email_jobs.sql
```

### Start command

From the repo root:

```bash
cd /opt/SAS/sas-api
python3 run_scheduler.py
```

### systemd

Copy the example unit in this folder to `/etc/systemd/system/sas-api-scheduler.service`, adjust paths and user if needed, then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sas-api-scheduler
sudo systemctl start sas-api-scheduler
sudo systemctl status sas-api-scheduler
```

### Suggested rollout

1. apply the SQL script
2. deploy code
3. install and start the scheduler service
4. confirm `/api/user/health` still shows recent scheduler runs
