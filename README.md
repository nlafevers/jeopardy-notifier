# Jeopardy Notifier - Deployment & Usage Guide

## Overview

**Jeopardy Notifier** is a web application that ranks employees based on hours worked at a specific assignment (adjusted for FTE) and sends personalized email notifications to each employee with their individual ranking.

The application is designed to:
- Accept two Excel spreadsheets: one with hours data and one with employee information
- Automatically rank employees by hours worked divided by their full-time equivalent (FTE) status
- Send personalized emails with each employee's unique ranking
- Respect privacy by permanently deleting all user-submitted data after emails are sent
- Prevent spam with bot detection (Cloudflare Turnstile)

---

## Prerequisites

Before deploying this application, you'll need:

1. **Google Cloud Platform (GCP) Account** - Free tier VM is sufficient
2. **Mailgun Account** - For sending emails (free tier available)
3. **Cloudflare Account** - For bot detection with Turnstile (free tier available)
4. **Python 3.11+** installed on your server
5. **Git** for cloning the repository
6. **Domain Name** (optional but recommended for emails)

---

## Step 1: Set Up Your Server (GCP)

### Create a VM Instance

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Navigate to **Compute Engine > VM Instances**
4. Click **Create Instance**
5. Configuration:
   - **Name:** `jeopardy-notifier` (or your choice)
   - **Region:** Choose closest to your users
   - **Machine Type:** `e2-micro` (free tier eligible)
   - **Boot Disk:** Ubuntu 22.04 LTS, 30GB
   - **Firewall:** Allow HTTP and HTTPS traffic

6. Click **Create** and wait for the instance to start

### Connect to Your VM

```bash
# Via Cloud Console, click SSH to open terminal, or use gcloud CLI:
gcloud compute ssh jeopardy-notifier --zone=YOUR_ZONE
```

---

## Step 2: Clone & Set Up the Application

### Install Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and tools
sudo apt install -y python3-pip python3-venv git

# Install uv for dependency management
pip3 install uv

# Clone repository
cd /home/$USER
git clone https://github.com/YOUR_REPO/jeopardy-notifier.git
cd jeopardy-notifier

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (using uv)
uv pip install django pandas openpyxl requests python-dotenv gunicorn
```

### Set Up Django

```bash
# Run database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
```

---

## Step 3: Configure API Keys

### Get Mailgun API Key

1. Sign up for [Mailgun](https://www.mailgun.com/) (free tier)
2. Go to **API > Keys** in left sidebar
3. Copy your **Private API Key**
4. From **Sending Domain**, copy your domain (e.g., `mg.yourdomain.com`)

### Get Cloudflare Turnstile Keys

1. Sign up for [Cloudflare](https://www.cloudflare.com/) (free tier)
2. Add your domain to Cloudflare
3. Go to **Turnstile** under your domain settings
4. Create a new Turnstile site
5. Copy **Site Key** and **Secret Key**

### Create Environment Configuration File

```bash
# Create .env file in project root
cat > /home/$USER/jeopardy-notifier/.env << EOF
# Mailgun Configuration
MAILGUN_API_KEY=your_mailgun_private_api_key_here
MAILGUN_DOMAIN=mg.yourdomain.com
MAILGUN_FROM_EMAIL=noreply@yourdomain.com

# Cloudflare Turnstile Configuration
TURNSTILE_SITE_KEY=your_turnstile_site_key_here
TURNSTILE_SECRET_KEY=your_turnstile_secret_key_here
REQUIRE_TURNSTILE=true

# Django Configuration
DEBUG=false
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
ALLOWED_HOSTS=your_domain.com,www.your_domain.com,your_vm_ip
CSRF_TRUSTED_ORIGINS=https://your_domain.com,https://www.your_domain.com
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=true
EOF

# Secure the .env file
chmod 600 /home/$USER/jeopardy-notifier/.env
```

The application already loads `.env` automatically in production and `.env.local` for local overrides, so no manual settings.py edits are needed.

---

## Step 4: Set Up Web Server (Gunicorn + Nginx)

### Install & Configure Gunicorn

```bash
source ~/.venv/bin/activate

# Create systemd service for Gunicorn
sudo tee /etc/systemd/system/jeopardy-notifier.service > /dev/null << EOF
[Unit]
Description=Jeopardy Notifier Django Application
After=network.target

[Service]
Type=notify
User=$USER
WorkingDirectory=/home/$USER/jeopardy-notifier
Environment="PATH=/home/$USER/jeopardy-notifier/.venv/bin"
ExecStart=/home/$USER/jeopardy-notifier/.venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind 127.0.0.1:8000 \
    jeopardy_notifier.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable jeopardy-notifier
sudo systemctl start jeopardy-notifier
sudo systemctl status jeopardy-notifier
```

### Install & Configure Nginx

```bash
sudo apt install -y nginx

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/jeopardy-notifier > /dev/null << 'EOF'
server {
    listen 80;
    server_name your_domain.com www.your_domain.com your_vm_ip;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/$USER/jeopardy-notifier/static/;
        expires 30d;
    }
}
EOF

# Enable the site
sudo ln -s /etc/nginx/sites-available/jeopardy-notifier /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Domain Setup

You can use just an IP address to your VM, but that will give a warning that the site is unsecure since SSL certificates are issued for domains only.  Add the external IP of the VM to the hosted zone A record for any domain and subdomains you want to use.  Then, take the nameservers from the hosted zone and update the nameservers at the domain registry (not the other way around).  

### Set Up HTTPS (Required for Production)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com -d www.your_domain.com
```

After HTTPS is enabled, confirm your Nginx config continues to send:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```

That header is required so Django can correctly recognize secure requests behind Nginx.

---

### Resolve Subdomain Issues

For some reason, although the subdomain was included in the nginx configuration as recommended above, it was necessary to remove the link to the default config in /etc/nginx/sites-enabled for the subdomain to work with https the same as the core domain.

## Step 5: Deploy

Your application is now live. Access it at:
- `https://your_domain.com`

---

## Step 6: Re-deployment

If it is necessary to restart the VM or restart the server on the VM and you get an SSL error from a machine that previously accessed the site, first try forcing a connection to the http version of the site.  Choose the option to proceed anyway.  This will force the machine to renew the SSL session, and might resolve the problem.

Also, if the VM is restarted and doesn't have a static IP, then the new IP will need to be updated in several places:
A records of DNS provider
/etc/nginx/sites-available/jeopardy-notifier server_name lines for both the listen 443 ssl server block and the listen 80 server block
.env file for ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS

## Usage Instructions

### For End Users

1. **Navigate to the application website**

2. **Upload Files:**
   - **Hours Report:** Excel file from Qgenda with employee hours by assignment
   - **Employee Info:** Excel file with employee names, emails, and FTE status

3. **Enter Assignment Name:**
   - The assignment you want to rank employees by (e.g., "Jeopardy 7a-7a")
   - Default value is provided

4. **Optional: Add Custom Message:**
   - Add any additional text you want included in the notification emails

5. **Verify You're Human:**
   - Complete the Cloudflare Turnstile verification

6. **Submit:**
   - Click "Upload and Rank"

7. **Review Rankings:**
   - Verify the rankings are correct
   - Employees with 0 hours are flagged
   - Choose "Send Emails" to proceed or update the selection before sending

8. **Confirmation:**
   - See confirmation that emails have been sent
   - All your data has been permanently deleted

### Excel File Formats

#### Hours Report
- Employee names in first column
- Assignments as column headers
- Hours for each assignment in the data
- Should include an "HA" (Hours Assigned) or similar suffix per assignment column

#### Employee Info
- Column headers: `Qgenda Name`, `First Name`, `Last Name`, `Email Addresses`, `FTE`
- One employee per row
- FTE values (e.g., 1.0 for full-time, 0.5 for part-time)

### Upload Limits

- Each uploaded spreadsheet must be an Excel file: `.xlsx`, `.xls`, or `.xlsm`
- Each file must be 5 MB or smaller

---

## Privacy & Data Security

**Important:** This application respects user privacy:

- ✅ No user data is stored permanently
- ✅ All uploaded files and ranking data are deleted immediately after emails are sent
- ✅ Abandoned workflows are cleared when a new upload session begins, and browser sessions expire automatically
- ✅ Each employee only receives their own ranking, not others' information
- ✅ No login or tracking of users
- ✅ Bot detection to prevent misuse

---

## Troubleshooting

### "Emails didn't send"
1. Check Mailgun API key is correct in `.env`
2. Verify domain is authorized in Mailgun
3. Check email addresses in the roster file are valid
4. Review Mailgun logs for bounce/rejection reasons

### "Verification failed"
- Refresh the page
- Check Turnstile keys are correct in `.env`
- Ensure `REQUIRE_TURNSTILE=true` in `.env`
- If deployed behind Nginx or another proxy, make sure HTTPS is working and `CSRF_TRUSTED_ORIGINS` matches your public `https://` URLs

### "Excel parsing error"
- Ensure Excel files have correct column names
- Check for merged cells or unusual formatting
- Try re-saving files as .xlsx (not .xls)
- Ensure each uploaded file is 5 MB or smaller

### Application redirects unexpectedly to HTTPS locally
- Set `DEBUG=true` in `.env.local`
- Leave `SECURE_SSL_REDIRECT=false` in local development
- Use `.env` for deployment values and `.env.local` only for local overrides

### Application won't start
```bash
# Check Gunicorn status
sudo systemctl status jeopardy-notifier

# View logs
sudo journalctl -u jeopardy-notifier -n 50

# Restart service
sudo systemctl restart jeopardy-notifier
```

### Nginx shows 502 Bad Gateway
- Ensure Gunicorn is running: `sudo systemctl status jeopardy-notifier`
- Check Nginx configuration: `sudo nginx -t`
- Restart Nginx: `sudo systemctl restart nginx`

---

## Support & Maintenance

### Update the Application

```bash
cd /home/$USER/jeopardy-notifier
git pull origin main
source .venv/bin/activate
uv pip install django pandas openpyxl requests python-dotenv gunicorn
python manage.py migrate
sudo systemctl restart jeopardy-notifier
```

### Monitor Application Health

```bash
# Check service status
sudo systemctl status jeopardy-notifier

# View recent logs
sudo journalctl -u jeopardy-notifier -n 100 -f
```

### Backup Your Configuration

```bash
# Backup .env file (keep this safe!)
sudo cp /home/$USER/jeopardy-notifier/.env /home/$USER/.env.backup
sudo chmod 600 /home/$USER/.env.backup
```

---

## Contact & Support

For issues or questions, contact your IT administrator or Django developer.

**Application Version:** 1.0  
**Last Updated:** March 2026
