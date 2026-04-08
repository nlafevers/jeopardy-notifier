# Local Development Setup

This guide explains how to run and test Jeopardy Notifier locally after the recent security hardening changes.

Yes, you can still test the app locally. The important difference is that Django now reads:

- `.env` for shared or deployment-style settings
- `.env.local` for local overrides

When both files exist, `.env.local` is loaded after `.env`, so local settings win.

## Prerequisites

- Python 3.11 or higher
- Git
- A spreadsheet app for creating test Excel files

## Step 1: Clone and Install

```bash
git clone https://github.com/YOUR_REPO/jeopardy-notifier.git
cd jeopardy-notifier

python3 -m venv .venv
source .venv/bin/activate

pip install django pandas openpyxl requests python-dotenv gunicorn
```

## Step 2: Create Local Settings

Create `.env.local` in the project root:

```bash
cat > .env.local << EOF
# Django
DEBUG=true
SECRET_KEY=local-development-secret-key-only
ALLOWED_HOSTS=localhost,127.0.0.1

# Keep HTTPS-only settings off locally unless you are explicitly testing them
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=false
SECURE_HSTS_PRELOAD=false
CSRF_TRUSTED_ORIGINS=

# Short-lived workflow/session data
SESSION_COOKIE_AGE=1800

# Mailgun (optional for local testing)
MAILGUN_API_KEY=
MAILGUN_DOMAIN=
MAILGUN_FROM_EMAIL=noreply@example.com

# Turnstile
# Option 1: disable locally
REQUIRE_TURNSTILE=false
TURNSTILE_SITE_KEY=
TURNSTILE_SECRET_KEY=
EOF
```

Notes:

- If you already have a production-style `.env`, you do not need to remove it. `.env.local` will override it locally.
- If you want to test Turnstile locally, set `REQUIRE_TURNSTILE=true` and use Cloudflare’s testing keys in `.env.local`.

Example Turnstile local-testing section:

```bash
REQUIRE_TURNSTILE=true
TURNSTILE_SITE_KEY=your_turnstile_test_site_key
TURNSTILE_SECRET_KEY=your_turnstile_test_secret_key
```

## Step 3: Initialize the Database

```bash
python manage.py migrate
```

If you want local behavior to match Cloud Run more closely, set `DATABASE_URL` to a Postgres instance instead of relying on the default SQLite database.

## Step 4: Run the App Locally

```bash
python manage.py runserver
```

Open:

- `http://127.0.0.1:8000/`
- or `http://localhost:8000/`

With `DEBUG=true`, local testing should work normally without HTTPS redirects.

## Step 5: Run Automated Tests

```bash
python manage.py test core.tests
```

This currently covers:

- Turnstile-required form validation
- valid Turnstile submission handling
- spreadsheet type validation
- spreadsheet size validation
- workflow session cleanup
- `POST`-only protection on the email-send endpoint

## Local Testing Modes

### Fastest Local Testing

Use:

- `DEBUG=true`
- `REQUIRE_TURNSTILE=false`
- blank Mailgun credentials

This lets you test the upload, verification, and confirmation flow without external services.

### Local Turnstile Testing

Use:

- `DEBUG=true`
- `REQUIRE_TURNSTILE=true`
- Turnstile testing keys in `.env.local`

This lets you verify the human-check flow locally.

### Local Mailgun Testing

If you want to exercise the real email path locally, add valid Mailgun credentials to `.env.local`.

If you do not want real emails sent, leave Mailgun credentials blank and avoid the final send step.

## Creating Test Excel Files

### Hours Report

The parser expects:

- employee names in column A, starting on row 6
- assignment names on row 3
- `HA` markers on row 5 for the assignment-hour columns
- employee rows ending at the first blank name or `Totals`

Minimal structure:

- Row 3: assignment names
- Row 5: measure labels including `HA`
- Row 6+: employee rows

### Employee Roster

Use columns:

```text
Qgenda Name | Email Name | Email Addresses | FTE
```

Notes:

- `Qgenda Name` must match the names used in the hours report
- `Email Name` is the display name used in outbound emails
- `Email Addresses` is the expected roster column heading
- each uploaded spreadsheet must be `.xlsx`, `.xls`, or `.xlsm`
- each file must be 5 MB or smaller

## Manual Local Test Checklist

1. Start the server with `python manage.py runserver`.
2. Open `http://localhost:8000/`.
3. Upload a valid hours spreadsheet and roster spreadsheet.
4. Confirm the ranking page appears and scores are correct.
5. Uncheck one or more employees and click `Update Selection`.
6. Confirm the ranking table refreshes with only the selected employees.
7. Click `Send Emails` only if you have intentionally configured Mailgun for local testing.
8. Confirm the confirmation page appears and the workflow session is cleared.

Useful scenarios to try:

- employee with 0 hours
- different FTE values affecting rank
- custom message included
- invalid file type such as `.txt`
- spreadsheet larger than 5 MB
- Turnstile enabled with local testing keys

## Session and Privacy Behavior in Local Testing

The app now clears workflow session data when a new upload session starts, and browser sessions expire automatically.

That means:

- returning to the upload page starts a fresh workflow
- abandoned uploads should not linger indefinitely in the active browser session
- the confirmation page flushes the session after completion

## Troubleshooting

### App redirects to HTTPS locally

Make sure `.env.local` contains:

```bash
DEBUG=true
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
SECURE_HSTS_SECONDS=0
```

### CSRF errors locally

This usually means your local settings are still inheriting production-style values from `.env`.

Confirm `.env.local` overrides:

```bash
DEBUG=true
CSRF_TRUSTED_ORIGINS=
SECURE_SSL_REDIRECT=false
```

Then restart `runserver`.

### Turnstile succeeds visually but form still fails

Check:

- `REQUIRE_TURNSTILE=true` is set in `.env.local`
- the testing site key and secret key match
- the page is loading the current local code
- your browser devtools show a non-empty `turnstile_response` field at submit time

### Spreadsheet parsing error

Check:

- row layout matches the expected parser format
- roster column names are correct
- file extension is `.xlsx`, `.xls`, or `.xlsm`
- file size is 5 MB or smaller

### `SECRET_KEY must be set when DEBUG is false`

Your local environment is behaving like production. Set:

```bash
DEBUG=true
```

in `.env.local`, then restart the server.

### `No module named ...`

Activate the virtual environment first:

```bash
source .venv/bin/activate
```

Then install dependencies again if needed.

## After Local Testing

When you are ready to deploy:

1. keep production values in `.env`
2. keep local-only overrides in `.env.local`
3. set a strong random production `SECRET_KEY`
4. set real `ALLOWED_HOSTS`
5. set real `CSRF_TRUSTED_ORIGINS` with your public `https://` URLs
6. enable Turnstile in production with `REQUIRE_TURNSTILE=true`
