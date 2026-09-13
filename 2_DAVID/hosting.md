# Home Hosting Commands

Replace `KC_DOMAIN.COM` and `SAS_DOMAIN.COM` in this file before running their commands. Enter real secrets when each `.env` file opens.

Before commands: reserve the server's LAN IP in the router, forward TCP ports `80` and `443` to it, and create DNS `A` records for both domains pointing to your public IP.

## 1. Server Setup

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx python3-venv python3-pip nodejs npm certbot python3-certbot-nginx ufw
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo systemctl enable --now nginx
```

## 2. SSH Key Login

Run these commands on the computer you will use to connect to the server. Replace `SERVER_LAN_IP` with the server's LAN IP address.

```bash
ssh-keygen -t ed25519 -a 100
ssh-copy-id agentbot@SERVER_LAN_IP
ssh agentbot@SERVER_LAN_IP
```

Keep that first connection open. In a second terminal on your computer, confirm this also connects without asking for the server password:

```bash
ssh agentbot@SERVER_LAN_IP
```

Only after that test succeeds, run these commands on the server:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
sudo sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sshd -t && sudo systemctl restart ssh
```

SSH keys are recommended before disabling password login: the private key stays on your computer, so a guessed or reused server password cannot sign in. Keep passwords enabled until the second connection succeeds so you cannot lock yourself out.

## 3. GitHub Access

Run this once. Add the printed public key to your GitHub account's SSH keys before cloning.

```bash
sudo -u agentbot mkdir -p /home/agentbot/.ssh
sudo -u agentbot test -f /home/agentbot/.ssh/id_ed25519 || sudo -u agentbot ssh-keygen -t ed25519 -N "" -f /home/agentbot/.ssh/id_ed25519
sudo cat /home/agentbot/.ssh/id_ed25519.pub
```

## 4. KC

```bash
sudo mkdir -p /srv/kc
sudo chown agentbot:agentbot /srv/kc
sudo -u agentbot git clone git@github.com:david-lytikainen/kc-api.git /srv/kc/api
sudo -u agentbot git clone git@github.com:david-lytikainen/kc-ui.git /srv/kc/ui
sudo -u agentbot python3 -m venv /srv/kc/venv
sudo -u agentbot /srv/kc/venv/bin/pip install --upgrade pip
sudo -u agentbot /srv/kc/venv/bin/pip install -r /srv/kc/api/requirements.txt
sudo -u agentbot nano /srv/kc/.env
sudo chmod 600 /srv/kc/.env
```

Add these lines to `/srv/kc/.env`, plus all real KC database, email, AWS, Stripe, and admin secrets:

```text
PUBLIC_APP_BASE_URL=https://KC_DOMAIN.COM
CORS_ORIGINS=https://KC_DOMAIN.COM
```

```bash
sudo -u agentbot bash -c 'cd /srv/kc/ui && REACT_APP_API_BASE_URL=https://KC_DOMAIN.COM/api npm ci && REACT_APP_API_BASE_URL=https://KC_DOMAIN.COM/api npm run build'
sudo tee /etc/systemd/system/kc.service >/dev/null <<'EOF'
[Unit]
Description=KC API
After=network.target

[Service]
User=agentbot
Group=agentbot
WorkingDirectory=/srv/kc/api
EnvironmentFile=/srv/kc/.env
ExecStart=/srv/kc/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now kc
```

```bash
sudo tee /etc/nginx/sites-available/kc >/dev/null <<'EOF'
server {
    listen 80;
    server_name KC_DOMAIN.COM;
    root /srv/kc/ui/build;
    index index.html;
    client_max_body_size 25m;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/kc /etc/nginx/sites-enabled/kc
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d KC_DOMAIN.COM
sudo certbot renew --dry-run
```

## 5. SAS

```bash
sudo mkdir -p /srv/sas
sudo chown agentbot:agentbot /srv/sas
sudo -u agentbot git clone git@github.com:david-lytikainen/sas-api.git /srv/sas/api
sudo -u agentbot git clone git@github.com:david-lytikainen/sas-ui.git /srv/sas/ui
sudo -u agentbot python3 -m venv /srv/sas/venv
sudo -u agentbot /srv/sas/venv/bin/pip install --upgrade pip
sudo -u agentbot /srv/sas/venv/bin/pip install -r /srv/sas/api/requirements.txt
sudo -u agentbot nano /srv/sas/.env
sudo chmod 600 /srv/sas/.env
```

Add these lines to `/srv/sas/.env`, plus every required SAS database, email, Stripe, and JWT secret:

```text
CLIENT_URL=https://SAS_DOMAIN.COM
CORS_ORIGINS=https://SAS_DOMAIN.COM
STRIPE_CONNECT_REFRESH_URL=https://SAS_DOMAIN.COM/events
STRIPE_CONNECT_RETURN_URL=https://SAS_DOMAIN.COM/events
STRIPE_CHECKOUT_SUCCESS_URL=https://SAS_DOMAIN.COM/events?checkout=success
STRIPE_CHECKOUT_CANCEL_URL=https://SAS_DOMAIN.COM/events?checkout=cancelled
```

```bash
sudo -u agentbot bash -c 'cd /srv/sas/ui/client && REACT_APP_API_URL=https://SAS_DOMAIN.COM npm ci && REACT_APP_API_URL=https://SAS_DOMAIN.COM npm run build'
sudo tee /etc/systemd/system/sas.service >/dev/null <<'EOF'
[Unit]
Description=SAS API
After=network.target

[Service]
User=agentbot
Group=agentbot
WorkingDirectory=/srv/sas/api
EnvironmentFile=/srv/sas/.env
ExecStart=/srv/sas/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo tee /etc/systemd/system/sas-scheduler.service >/dev/null <<'EOF'
[Unit]
Description=SAS Scheduler
After=network.target

[Service]
User=agentbot
Group=agentbot
WorkingDirectory=/srv/sas/api
EnvironmentFile=/srv/sas/.env
ExecStart=/srv/sas/venv/bin/python run_scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now sas sas-scheduler
```

```bash
sudo tee /etc/nginx/sites-available/sas >/dev/null <<'EOF'
server {
    listen 80;
    server_name SAS_DOMAIN.COM;
    root /srv/sas/ui/client/build;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /sounds/ {
        proxy_pass http://127.0.0.1:8000;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/sas /etc/nginx/sites-enabled/sas
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d SAS_DOMAIN.COM
sudo certbot renew --dry-run
```

## 6. Deploy Updates

```bash
sudo -u agentbot git -C /srv/kc/api pull
sudo -u agentbot git -C /srv/kc/ui pull
sudo -u agentbot /srv/kc/venv/bin/pip install -r /srv/kc/api/requirements.txt
sudo -u agentbot bash -c 'cd /srv/kc/ui && REACT_APP_API_BASE_URL=https://KC_DOMAIN.COM/api npm ci && REACT_APP_API_BASE_URL=https://KC_DOMAIN.COM/api npm run build'
sudo systemctl restart kc

sudo -u agentbot git -C /srv/sas/api pull
sudo -u agentbot git -C /srv/sas/ui pull
sudo -u agentbot /srv/sas/venv/bin/pip install -r /srv/sas/api/requirements.txt
sudo -u agentbot bash -c 'cd /srv/sas/ui/client && REACT_APP_API_URL=https://SAS_DOMAIN.COM npm ci && REACT_APP_API_URL=https://SAS_DOMAIN.COM npm run build'
sudo systemctl restart sas sas-scheduler

sudo nginx -t && sudo systemctl reload nginx
```

## 7. Logs

```bash
sudo systemctl status kc sas sas-scheduler nginx certbot.timer
sudo journalctl -u kc -f
sudo journalctl -u sas -f
sudo journalctl -u sas-scheduler -f
```
