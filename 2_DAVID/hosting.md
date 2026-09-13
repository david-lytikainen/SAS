# Home Hosting Commands

Run these commands on a clean Ubuntu 24.04 server. Replace every ALL-CAPS value first.

Manual steps before the commands:

1. Reserve the server's LAN IP in the router, for example `192.168.1.50`.
2. Forward router TCP ports `80` and `443` to that IP.
3. Point the domain's DNS `A` record to the public IP shown by `curl https://api.ipify.org`.

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

Use an SSH key, test it in a second terminal, then disable SSH passwords:

```bash
sudo sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sshd -t && sudo systemctl restart ssh
```

## 2. KC: FastAPI, Uvicorn, React

Set these values:

```bash
export APP=kc
export DOMAIN=KC_DOMAIN.COM
export API_REPO=KC_API_GIT_URL
export UI_REPO=KC_UI_GIT_URL
```

Create the service user and download both repositories:

```bash
sudo adduser --system --group --home /srv/$APP $APP
sudo mkdir -p /srv/$APP
sudo chown $APP:$APP /srv/$APP
sudo -u $APP mkdir -p /srv/$APP/.ssh
sudo -u $APP ssh-keygen -t ed25519 -N "" -f /srv/$APP/.ssh/id_ed25519
sudo cat /srv/$APP/.ssh/id_ed25519.pub
```

If the repositories are private, add that public key to your GitHub account's SSH keys, then use `git@github.com:OWNER/REPOSITORY.git` for both repository values.

```bash
sudo -u $APP git clone "$API_REPO" /srv/$APP/api
sudo -u $APP git clone "$UI_REPO" /srv/$APP/ui
sudo -u $APP python3 -m venv /srv/$APP/venv
sudo -u $APP /srv/$APP/venv/bin/pip install --upgrade pip
sudo -u $APP /srv/$APP/venv/bin/pip install -r /srv/$APP/api/requirements.txt
```

Create `/srv/kc/.env` with the real KC secrets. `PUBLIC_APP_BASE_URL` and `CORS_ORIGINS` must use your domain:

```bash
sudo -u $APP nano /srv/$APP/.env
sudo chmod 600 /srv/$APP/.env
```

Add at least these values to that file:

```text
PUBLIC_APP_BASE_URL=https://KC_DOMAIN.COM
CORS_ORIGINS=https://KC_DOMAIN.COM
```

Build the frontend with the same-origin API address:

```bash
sudo -u $APP bash -c "cd /srv/$APP/ui && REACT_APP_API_BASE_URL=https://$DOMAIN/api npm ci && REACT_APP_API_BASE_URL=https://$DOMAIN/api npm run build"
```

Create the Uvicorn service:

```bash
sudo tee /etc/systemd/system/$APP.service >/dev/null <<EOF
[Unit]
Description=KC API
After=network.target

[Service]
User=$APP
Group=www-data
WorkingDirectory=/srv/$APP/api
EnvironmentFile=/srv/$APP/.env
ExecStart=/srv/$APP/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now $APP
```

Create the Nginx site. The trailing slash in `proxy_pass` removes `/api/` before KC receives the request:

```bash
sudo tee /etc/nginx/sites-available/$DOMAIN >/dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    root /srv/$APP/ui/build;
    index index.html;
    client_max_body_size 25m;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d $DOMAIN
sudo certbot renew --dry-run
```

## 3. SAS: Flask, Gunicorn, React, Scheduler

Run the same steps above with these values and changes:

```bash
export APP=sas
export DOMAIN=SAS_DOMAIN.COM
export API_REPO=SAS_API_GIT_URL
export UI_REPO=SAS_UI_GIT_URL
```

Create the service user, download the repositories, install Python packages, and create the SAS secrets file:

```bash
sudo adduser --system --group --home /srv/$APP $APP
sudo mkdir -p /srv/$APP
sudo chown $APP:$APP /srv/$APP
sudo -u $APP mkdir -p /srv/$APP/.ssh
sudo -u $APP ssh-keygen -t ed25519 -N "" -f /srv/$APP/.ssh/id_ed25519
sudo cat /srv/$APP/.ssh/id_ed25519.pub
```

If the repositories are private, add that public key to your GitHub account's SSH keys, then use `git@github.com:OWNER/REPOSITORY.git` for both repository values.

```bash
sudo -u $APP git clone "$API_REPO" /srv/$APP/api
sudo -u $APP git clone "$UI_REPO" /srv/$APP/ui
sudo -u $APP python3 -m venv /srv/$APP/venv
sudo -u $APP /srv/$APP/venv/bin/pip install --upgrade pip
sudo -u $APP /srv/$APP/venv/bin/pip install -r /srv/$APP/api/requirements.txt
sudo -u $APP nano /srv/$APP/.env
sudo chmod 600 /srv/$APP/.env
```

Add the real SAS secrets to `.env`. At minimum, use your domain in these values:

```text
CLIENT_URL=https://SAS_DOMAIN.COM
CORS_ORIGINS=https://SAS_DOMAIN.COM
STRIPE_CONNECT_REFRESH_URL=https://SAS_DOMAIN.COM/events
STRIPE_CONNECT_RETURN_URL=https://SAS_DOMAIN.COM/events
STRIPE_CHECKOUT_SUCCESS_URL=https://SAS_DOMAIN.COM/events?checkout=success
STRIPE_CHECKOUT_CANCEL_URL=https://SAS_DOMAIN.COM/events?checkout=cancelled
```

The SAS UI is in the `client` folder. Build it with:

```bash
sudo -u $APP bash -c "cd /srv/$APP/ui/client && REACT_APP_API_URL=https://$DOMAIN npm ci && REACT_APP_API_URL=https://$DOMAIN npm run build"
```

Use this Gunicorn service instead of the KC Uvicorn service:

```bash
sudo tee /etc/systemd/system/$APP.service >/dev/null <<EOF
[Unit]
Description=SAS API
After=network.target

[Service]
User=$APP
Group=www-data
WorkingDirectory=/srv/$APP/api
EnvironmentFile=/srv/$APP/.env
ExecStart=/srv/$APP/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now $APP
```

Use this Nginx site instead of the KC Nginx site. SAS already has `/api/` routes, so there is no trailing slash after port `8000`:

```bash
sudo tee /etc/nginx/sites-available/$DOMAIN >/dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    root /srv/$APP/ui/client/build;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /sounds/ {
        proxy_pass http://127.0.0.1:8000;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d $DOMAIN
sudo certbot renew --dry-run
```

SAS also needs its scheduler worker:

```bash
sudo tee /etc/systemd/system/sas-scheduler.service >/dev/null <<EOF
[Unit]
Description=SAS Scheduler
After=network.target

[Service]
User=sas
Group=www-data
WorkingDirectory=/srv/sas/api
EnvironmentFile=/srv/sas/.env
ExecStart=/srv/sas/venv/bin/python run_scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now sas-scheduler
```

## 4. Deploy Updates

Run these for KC. Change `kc` to `sas` and use `ui/client` for SAS:

```bash
export APP=kc
export DOMAIN=KC_DOMAIN.COM
sudo -u $APP git -C /srv/$APP/api pull
sudo -u $APP git -C /srv/$APP/ui pull
sudo -u $APP /srv/$APP/venv/bin/pip install -r /srv/$APP/api/requirements.txt
sudo -u $APP bash -c "cd /srv/$APP/ui && REACT_APP_API_BASE_URL=https://$DOMAIN/api npm ci && REACT_APP_API_BASE_URL=https://$DOMAIN/api npm run build"
sudo systemctl restart $APP
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl status $APP
```

For SAS, restart both services:

```bash
sudo systemctl restart sas sas-scheduler
```

## 5. Check Problems

```bash
sudo systemctl status kc
sudo systemctl status sas
sudo systemctl status sas-scheduler
sudo journalctl -u kc -f
sudo journalctl -u sas -f
sudo journalctl -u sas-scheduler -f
sudo nginx -t
sudo systemctl status certbot.timer
```
