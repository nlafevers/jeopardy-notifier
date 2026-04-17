# Jeopardy Notifier TESTING

This guide explains how to run and test Jeopardy Notifier locally.

- `.env` for shared or deployment-style settings
- `.env.local` for local overrides

When both files exist, `.env.local` is loaded after `.env`, so local settings win.

## Prerequisites

For local testing it is only necessary to have `python` and `uv` installed.  However, it is possible to use Mailgun and Turnstile from the local testing environment if you have these accounts setup.

## Download and Extract

1. Download the latest release from [Github](https://github.com/nlafevers/jeopardy-notifier/releases)
2. Extract
3. `cd jeopardy-notifier-VER/jeopardy-notifier-VER`
4. `uv sync`

## Create Local Settings

Rename `sample.env.local` to `.env.local`, then adjust the variables as needed.

Keep HTTPS-only settings off locally unless you are explicitly testing them.

    SECURE_SSL_REDIRECT=false
    SESSION_COOKIE_SECURE=false
    CSRF_COOKIE_SECURE=false
    SECURE_HSTS_SECONDS=0
    SECURE_HSTS_INCLUDE_SUBDOMAINS=false
    SECURE_HSTS_PRELOAD=false
    CSRF_TRUSTED_ORIGINS=

For a short-lived workflow and session data:

    SESSION_COOKIE_AGE=1800

Mailgun and Turnstile are optional for local testing.

Notes:

- If you already have a production-style `.env`, you do not need to remove it. `.env.local` will override it locally.
- If you want to test Turnstile locally, set `REQUIRE_TURNSTILE=true` and use Cloudflare’s testing keys in `.env.local`.

## Initialize the Database

```bash
python manage.py migrate
```

If you want local behavior to match Cloud Run more closely, set `DATABASE_URL` to a Postgres instance instead of relying on the default SQLite database.

## Run the App Locally

```bash
python manage.py runserver
```

Open:

- `http://127.0.0.1:8000/`
- or `http://localhost:8000/`

With `DEBUG=true`, local testing should work normally without HTTPS redirects.

## Run Automated Tests

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

- The assignment names in the third row, each spanning six columns
- The six quantities being tallied for each assignment on the fifth row
- One of the quantities being tallied to be `HA` (actual hours)
- Employee names in the first column starting on row six

The parser will pull actual hours from the designated assignment for each employee until it reaches an empty row in the first column or the word `Totals`

### Roster

The roster must contain exactly these columns in this order:

```text
Qgenda Name | Email Name | Email Addresses | FTE
```

Multiple email addresses can be listed for each employee separated by commas.

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

The app clears workflow session data when a new upload session starts, and browser sessions expire automatically.

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
- the testing site key and secret key are correct
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