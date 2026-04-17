# Jeopardy Notifier README

## Overview

**Jeopardy Notifier** is a Django web application that ranks employees by hours worked at a particular assignment, divided by FTE, and sends each one a personalized email showing their ranking.  The version 1.1 release is built for direct deployment on a VM.  The version 1.2 release is built for serverless containerized deployment, particularly GCP Cloud Run.

## Usage

The application does not store any data between sessions, so both the report of employee hours, and a roster of employee names, emails, and FTE, must be uploaded with each use.  There is no login required, but Cloudflare Turnstile prevents form submission by bots.  The user is provided a preview of the rankings and may deselect individuals to to either re-rank the rest, or exclude those deselected from receiving emails without re-ranking.  The application is built to use Mailgun for sending emails.  The application does not store data between sessions, and actively clears data if the session appears abandoned or once emails have been sent.

## Prerequisites

For local testing it is only necessary to have `python` and `uv` installed.  However, it is possible to use Mailgun and Turnstile from the local testing environment if you have these accounts setup.

For deployment to GCP Cloud Run, the following is needed:
1. A GCP project with billing enabled
2. Cloud Run, Cloud Build, and Artifact Registry APIs enabled
3. A Mailgun account
4. A Cloudflare Turnstile widget for your domain

## Testing

See TESTING.md for more details on testing the application in a local environment.

## Deployment

See DEPLOYMENT.md for more details on deploying the application to GCP Cloud Run.

## Architecture Notes for Ver 1.2

Cloud Run changes a few assumptions compared with a VM:

- the container must listen on the provided `PORT`
- startup should only start the web server, not run migrations
- logs should go to stdout/stderr so they appear in Cloud Logging
- local disk is ephemeral and not shared between instances
- Django session data should live in a shared database if you may scale past one instance

This app stores ranking data in the session between requests. For a free-tier, single-instance deployment, it can still run with the default SQLite database inside the container. If `DATABASE_URL` is omitted, the container now runs Django migrations on startup and uses SQLite automatically.

## Spreadsheet Formats

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

## Operational Recommendations

- Keep request concurrency low at first because spreadsheet parsing and outbound email sending are synchronous.
- For a free-tier setup, prefer a single instance and SQLite, understanding that workflow/session data can be lost if Cloud Run stops or replaces the container mid-session.
- Consider moving the email-sending step to a background job if sends become slow or unreliable.
- Rotate any credentials that were ever committed to local files.
- If you add a custom domain, update both `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
