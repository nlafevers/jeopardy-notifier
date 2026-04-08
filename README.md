# Jeopardy Notifier - Cloud Run Deployment & Usage Guide

## Overview

**Jeopardy Notifier** is a Django web application that:

- accepts two Excel spreadsheets
- ranks employees by hours worked divided by FTE
- lets a human verify the ranking before sending
- sends personalized emails through Mailgun
- clears workflow data after completion

This project now targets **GCP Cloud Run** rather than a long-lived VM.

## Architecture Notes for Cloud Run

Cloud Run changes a few assumptions compared with a VM:

- the container must listen on the provided `PORT`
- startup should only start the web server, not run migrations
- logs should go to stdout/stderr so they appear in Cloud Logging
- local disk is ephemeral and not shared between instances
- Django session data should live in a shared database if you may scale past one instance

This app stores ranking data in the session between requests. For a free-tier, single-instance deployment, it can still run with the default SQLite database inside the container. If `DATABASE_URL` is omitted, the container now runs Django migrations on startup and uses SQLite automatically.

## Prerequisites

Before deploying, prepare:

1. A GCP project with billing enabled
2. Cloud Run, Cloud Build, Artifact Registry, and Cloud SQL APIs enabled
3. A Mailgun account
4. A Cloudflare Turnstile site
5. `gcloud` installed locally

## Required Environment Variables

Set these for production:

```bash
DEBUG=false
SECRET_KEY=replace-me
ALLOWED_HOSTS=.run.app,your-domain.example
CSRF_TRUSTED_ORIGINS=https://your-domain.example
MAILGUN_API_KEY=replace-me
MAILGUN_DOMAIN=mg.your-domain.example
MAILGUN_FROM_EMAIL=no-reply@your-domain.example
TURNSTILE_SITE_KEY=replace-me
TURNSTILE_SECRET_KEY=replace-me
REQUIRE_TURNSTILE=true
LOG_LEVEL=INFO
```

`DATABASE_URL` is optional. If you leave it unset, the app uses SQLite.

Use Secret Manager for sensitive values like `SECRET_KEY`, `MAILGUN_API_KEY`, and `TURNSTILE_SECRET_KEY`.

## Local Validation

From the repo root:

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Deploying to Cloud Run

### 1. Build the image

```bash
gcloud builds submit --tag northamerica-northeast1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/jeopardy-notifier
```

### 2. Choose a database mode

For the lowest-cost deployment, do nothing else here and let the app use SQLite.

If you prefer a persistent shared database, set `DATABASE_URL` and run migrations separately before or alongside deployment:

```bash
uv run python manage.py migrate
```

### 3. Deploy the service

For your lowest-cost SQLite deployment, use this as the starting point:

```bash
gcloud run deploy jeopardy-notifier \
  --image northamerica-northeast1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/jeopardy-notifier \
  --region northamerica-northeast1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 1 \
  --set-env-vars DEBUG=false,ALLOWED_HOSTS=.run.app,your-domain.example,CSRF_TRUSTED_ORIGINS=https://your-domain.example,MAILGUN_DOMAIN=mg.your-domain.example,MAILGUN_FROM_EMAIL=no-reply@your-domain.example,TURNSTILE_SITE_KEY=replace-me,REQUIRE_TURNSTILE=true,LOG_LEVEL=INFO \
  --set-secrets SECRET_KEY=django-secret:latest,MAILGUN_API_KEY=mailgun-api-key:latest,TURNSTILE_SECRET_KEY=turnstile-secret:latest
```

That command intentionally does not set `DATABASE_URL`, so the container will use SQLite and run `migrate` during startup.

The most important SQLite-specific flag here is `--max-instances 1`, which avoids multiple Cloud Run instances each having their own separate local database file.

If you use an external Cloud SQL database, also include:

```bash
--add-cloudsql-instances YOUR_PROJECT:northamerica-northeast1:YOUR_INSTANCE
```

## Logging and Health Checks

- Application and Django logs are written to stdout/stderr for Cloud Logging.
- Gunicorn access and error logs are enabled in the container command.
- A basic health endpoint is available at `/health/`.

If a revision fails to become healthy, check:

1. Cloud Run revision logs
2. Whether `SECRET_KEY` is set
3. Whether `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` include the active hostname
4. If using `DATABASE_URL`, whether that database is reachable from Cloud Run
5. If using SQLite, whether startup completed and migrations ran successfully

## Usage

1. Open the app in a browser.
2. Complete the Turnstile check if enabled.
3. Upload the hours report and roster spreadsheet.
4. Review the ranking page.
5. Update the selected recipients if needed.
6. Send the emails.
7. Confirm the completion page appears.

## Spreadsheet Formats

### Hours report

The parser expects:

- employee names in column A starting on row 6
- assignment names on row 3
- `HA` markers on row 5 for hour columns
- rows ending at the first blank name or `Totals`

### Roster

The roster must contain exactly these columns in this order:

```text
Qgenda Name | Email Name | Email Addresses | FTE
```

## Operational Recommendations

- Keep request concurrency low at first because spreadsheet parsing and outbound email sending are synchronous.
- For a free-tier setup, prefer a single instance and SQLite, understanding that workflow/session data can be lost if Cloud Run stops or replaces the container mid-session.
- Consider moving the email-sending step to a background job if sends become slow or unreliable.
- Rotate any credentials that were ever committed to local files.
- If you add a custom domain, update both `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
