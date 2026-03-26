# Local Development Setup

This guide walks you through setting up the Jeopardy Notifier application for local development and testing.

## Prerequisites

- Python 3.11 or higher
- Git
- A code editor (VS Code, PyCharm, etc.)
- Excel or a spreadsheet application (to create test files)

## Step 1: Clone & Set Up

```bash
# Clone the repository
git clone https://github.com/YOUR_REPO/jeopardy-notifier.git
cd jeopardy-notifier

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install django pandas openpyxl requests python-dotenv
```

## Step 2: Set Up Environment Variables

Create a `.env.local` file in the project root (this is local-only, don't commit):

```bash
cat > .env.local << EOF
# Django settings
DEBUG=true
SECRET_KEY=dev-secret-key-not-for-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Mailgun (optional for development - can test without)
MAILGUN_API_KEY=
MAILGUN_DOMAIN=
MAILGUN_FROM_EMAIL=noreply@example.com

# Cloudflare Turnstile (optional for development)
TURNSTILE_SITE_KEY=
TURNSTILE_SECRET_KEY=
REQUIRE_TURNSTILE=false
EOF
```

## Step 3: Configure Django Settings for Development

Update `jeopardy_notifier/settings.py` to load `.env.local` for development:

```python
# At the very top of settings.py, add:
import os
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')  # Load local dev settings
except ImportError:
    pass

# Then update these settings:
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
```

## Step 4: Initialize Database

```bash
# Create migrations (if not already done)
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# (Optional) Create a superuser for admin panel
python manage.py createsuperuser
```

## Step 5: Run Development Server

```bash
python manage.py runserver
```

You should see:
```
Starting development server at http://127.0.0.1:8000/
```

Open your browser to: **http://localhost:8000**

---

## Testing Without Real API Keys

### Test Email Sending (Without Mailgun)

For development/testing, you can log emails to the console instead of actually sending them:

```python
# In settings.py, add:
if DEBUG:
    # Log emails to console in development
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Use Mailgun in production
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
```

When emails would be sent, they'll appear in your terminal instead.

### Test Bot Detection (Without Turnstile)

Set `REQUIRE_TURNSTILE=false` in `.env.local` to skip bot verification during development. The form will submit without Turnstile validation.

---

## Creating Test Excel Files

### Hours Report Format

Create an Excel file named `test_hours.xlsx`:

```
Employee Name | Jeopardy 7a-7a HA | Other Assignment HA
John Doe      | 40                | 20
Jane Smith    | 35                | 25
Bob Johnson   | 45                | 15
Alice Brown   | 30                | 35
```

**Column headers:**
- Row 1: Assignment names
- Row 2: "HA" (Hours Assigned)
- Data starts in Row 3

### Employee Roster Format

Create an Excel file named `test_roster.xlsx`:

```
Qgenda Name | First Name | Last Name | Email              | FTE
John Doe    | John       | Doe       | john@example.com   | 1.0
Jane Smith  | Jane       | Smith     | jane@example.com   | 1.0
Bob Johnson | Bob        | Johnson   | bob@example.com    | 0.5
Alice Brown | Alice      | Brown     | alice@example.com  | 0.75
```

**Required columns:**
- `Qgenda Name` - Must match names in hours report
- `First Name` - Employee's first name
- `Last Name` - Employee's last name
- `Email` - Where notifications would be sent
- `FTE` - Full-time equivalent (1.0 = full-time, 0.5 = part-time, etc.)

---

## Testing the Full Workflow

### Manual Testing Steps

1. **Access upload form:**
   - Go to http://localhost:8000/
   - You should see the upload form

2. **Upload test files:**
   - Select `test_hours.xlsx` as the Hours Report
   - Select `test_roster.xlsx` as the Employee Roster
   - Enter assignment: `Jeopardy 7a-7a`
   - Add optional custom message
   - Click "Upload and Rank"

3. **Verify rankings:**
   - Should see employees ranked by hours/FTE
   - Any with 0 hours should be highlighted
   - You can go back and edit

4. **Test email sending:**
   - Click "Send Emails"
   - In development mode, emails appear in terminal (not actually sent)
   - Session data should be cleared

5. **Confirm:**
   - Should see confirmation page
   - Session should be cleared (session data gone)

### Test Cases to Try

**Test 1: Basic Ranking**
- All employees have hours
- Ranking calculated correctly (hours ÷ FTE)

**Test 2: Zero Hours**
- Add an employee with 0 hours in test data
- Verify they're flagged on verification page

**Test 3: Different FTE Values**
- Employee A: 40 hours, FTE 1.0 = Score 40
- Employee B: 40 hours, FTE 0.5 = Score 80 (ranked first!)
- Verify ranking is correct

**Test 4: Custom Message**
- Add custom message in upload form
- Verify it appears in email output

**Test 5: Back/Edit Workflow**
- Upload files, go through verification
- Click "Back and Edit"
- Should return to upload form with cleared data

---

## Debugging Tips

### View Console Output

The development server terminal shows:
- Django logs
- Email output (in console email backend)
- PHP/SQL queries (if DEBUG=true)
- Error tracebacks

### Access Admin Panel (Optional)

If you created a superuser, access admin at:
```
http://localhost:8000/admin/
```

Username and password: whatever you set up

### Check Session Data

Add debug logging in views.py to see what's stored in sessions:

```python
print(f"Session data: {request.session}")
```

### Database Inspection

View database records:

```bash
# Open Django shell
python manage.py shell

# Query examples:
from core.models import *

# View all records (if models are used)
# Model.objects.all()

exit()
```

---

## Troubleshooting

### "No module named 'openpyxl'"

```bash
pip install openpyxl
```

### "No module named 'django'"

Make sure virtual environment is activated:

```bash
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

### "Address already in use"

Port 8000 is already in use. Use a different port:

```bash
python manage.py runserver 8001
```

Then visit: http://localhost:8001

### Excel file not parsing correctly

- Ensure columns match expected names exactly
- Check for merged cells or extra formatting
- Try saving as `.xlsx` (not `.xls`)
- Verify headers are in correct rows

### Emails not showing in console

Make sure `DEBUG=true` in `.env.local` and `REQUIRE_TURNSTILE=false`

---

## Tips for Development

### Use Hot Reload

The development server automatically reloads when you change Python files. Just save and refresh your browser.

### Disable CSRF for Testing (Development Only)

You can temporarily disable CSRF protection while testing:

```python
# In settings.py (DEVELOPMENT ONLY!):
if DEBUG:
    MIDDLEWARE = [m for m in MIDDLEWARE if m != 'django.middleware.csrf.CsrfViewMiddleware']
```

### Use Django Shell for Testing

```bash
python manage.py shell

# Test URL routing:
from django.urls import reverse
print(reverse('upload'))  # /
print(reverse('verification'))  # /verification/
print(reverse('send_emails'))  # /send/
print(reverse('confirmation'))  # /confirmation/
```

---

## Next Steps

Once testing is complete:

1. **Fix any bugs** found during testing
2. **Optimize performance** if needed
3. **Follow README.md** for production deployment
4. **Set real API keys** in production `.env` file
5. **Enable Turnstile** by setting `REQUIRE_TURNSTILE=true`
