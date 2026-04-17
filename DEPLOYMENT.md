# Jeopardy Notifier DEPLOYMENT

## Prerequisites

1. A GCP project with billing enabled
2. Cloud Run, Cloud Build, and Artifact Registry APIs enabled
3. A Mailgun account
4. A Cloudflare Turnstile widget for your domain
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
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SECURE_HSTS_SECONDS=3600
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=true
```

`DATABASE_URL` is optional. If you leave it unset, the app uses SQLite.

Use Secret Manager for sensitive values like `SECRET_KEY`, `MAILGUN_API_KEY`, and `TURNSTILE_SECRET_KEY`.

## Initialize GCP

Login to your Google account: `gcloud auth login`

Set your active project: `gcloud config set project YOUR_PROJECT_ID`

Enable the required APIs:
    gcloud services enable run.googleapis.com \
                           cloudbuild.googleapis.com \
                           artifactregistry.googleapis.com \
                           secretmanager.googleapis.com

## Configure Secret Manager

Store secret keys for Django, Mailgun, and Turnstile:

    gcloud secrets create SECRET_KEY --replication-policy="automatic"
    echo -n "your-secret-key-here" | gcloud secrets versions add SECRET_KEY --data-file=-

    gcloud secrets create MAILGUN_API_KEY --replication-policy="automatic"
    echo -n "your-mailgun-key" | gcloud secrets versions add MAILGUN_API_KEY --data-file=-

    gcloud secrets create TURNSTILE_SECRET_KEY --replication-policy="automatic"
    echo -n "your-turnstile-secret" | gcloud secrets versions add TURNSTILE_SECRET_KEY --data-file=-

## Create the Artifact Registry

    gcloud artifacts repositories create app-images \
        --repository-format=docker \
        --location=YOUR_REGION \
        --description="Repository for Jeopardy Notifier images"

## Build the Container Image

    gcloud builds submit --tag YOUR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/app-images/jeopardy-notifier .

## Deploy to Cloud Run

    gcloud run deploy jeopardy-notifier \
        --image YOUR_REGION-docker.pkg.dev/YOUR_PROJECT_ID/app-images/jeopardy-notifier \
        --region YOUR_REGION \
        --allow-unauthenticated \
        --set-env-vars "DEBUG=false,ALLOWED_HOSTS=.run.app,your-domain.example,CSRF_TRUSTED_ORIGINS=https://your-domain.example,MAILGUN_DOMAIN=mg.your-domain.example,MAILGUN_FROM_EMAIL=no-reply@your-domain.example,TURNSTILE_SITE_KEY=replace-me,REQUIRE_TURNSTILE=true,LOG_LEVEL=INFO,SECURE_SSL_REDIRECT=true,SESSION_COOKIE_SECURE=true,CSRF_COOKIE_SECURE=true,SECURE_HSTS_SECONDS=3600,SECURE_HSTS_INCLUDE_SUBDOMAINS=true,SECURE_HSTS_PRELOAD=true" \
        --update-secrets "SECRET_KEY=SECRET_KEY:latest,MAILGUN_API_KEY=MAILGUN_API_KEY:latest,TURNSTILE_SECRET_KEY=TURNSTILE_SECRET_KEY:latest"

## Deploy to Cloud Run

### 1. Build the image

```bash
gcloud builds submit --tag YOUR_REGION-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/jeopardy-notifier
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
  --image YOUR_REGION-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/jeopardy-notifier \
  --region YOUR_REGION \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 1 \
  --set-env-vars "DEBUG=false,ALLOWED_HOSTS=.run.app,your-domain.example,CSRF_TRUSTED_ORIGINS=https://your-domain.example,MAILGUN_DOMAIN=mg.your-domain.example,MAILGUN_FROM_EMAIL=no-reply@your-domain.example,TURNSTILE_SITE_KEY=replace-me,REQUIRE_TURNSTILE=true,LOG_LEVEL=INFO,SECURE_SSL_REDIRECT=true,SESSION_COOKIE_SECURE=true,CSRF_COOKIE_SECURE=true,SECURE_HSTS_SECONDS=3600,SECURE_HSTS_INCLUDE_SUBDOMAINS=true,SECURE_HSTS_PRELOAD=true" \
  --set-secrets "SECRET_KEY=SECRET_KEY:latest,MAILGUN_API_KEY=MAILGUN_API_KEY:latest,TURNSTILE_SECRET_KEY=TURNSTILE_SECRET_KEY:latest"
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
