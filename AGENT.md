# Jeopardy Notifier

This web application will rank employees based on the hours they have worked at a particular assignment, adjusted for FTE, and then send personalized emails to notify them of their individual ranking.  

## User Experience
The user should be able to access the application from any common desktop or mobile browser.  There will be no username or password required, but there will be bot detection to reduce inappropriate traffic.  Once verified as human, the user will be shown a form where they will upload two documents: an Excel spreadsheet showing employee work hours in all assignments, and an Excel spreadsheet listing employee information including first and last names, email addresses, and FTE status.  The submission form will include a space for the user to free text the assignment by which to rank the employees, and the default text in this box with be "Jeopardy 7a-7a". The submission form will also includean optional textbox for adding a custom message to be included in the email notifications.  After submission of this form, the user should be shown a verification page that shows the ranking of employees by hours in the chosen assignment divided by FTE.  From here the user will be able to choose to go back and make changes or send the notifications.  The user will then be shown a confirmation page.  The recipients of the emails will see only their own ranking, not the information for any other employee besides themself.

## Key Constraints & Design Decisions
- **Usage Frequency**: Called at most once per day, sometimes not for weeks
- **Scale**: Maximum 30 recipients
- **Architecture**: Simple web app with minimal database usage (SQLite or in-memory processing)
- **Hosting**: GCP VM (free tier)
- **Bot Detection**: Cloudflare Turnstile (free)
- **Email provider**: Mailgun (free tier)
- **Privacy**: The application will retain no user submitted information after the email notifications have been sent
- **Tools**: Use uv for managing project virtual environments and dependencies.  Use Django for the web app.  Use git for version control.  Use Github for hosting the repository.
- **Documentation**: Upon completion of any task, update this document to document the progress of the project.  Upon completion of the project write a README file to explain to non-technical users how to deploy and use the application.

## Functionality
1.  **Bot Detection:** There will be no login page, but only human users will be allowed to use the application.
2.  **Form Submission:** The user will upload two Excel spreadsheets and enter or modify to optional textboxes.
    *   **Hours Report:** A spreadsheet of the hours each employee has worked in various assignments.
    *   **Employee Info:** A spreadsheet containing the names of the employees as used in the hours report, employee first name, last name, email addresses, and FTE (full time equivalents).
    *   **Assignment to Rank:** The assignment by which the employees will be ranked by hours worked.  The default will be "Jeopardy 7a-7a".
    *   **Custom Message:** An optional additional text message to add to the notification email.
3.  **Ranking:** The application will create a ranked list of the employees by the number of hours they have worked in the chosen assignment divided by their FTE.
4.  **Verification:** After submission of the form the user will be shown the ranking before being presented with a choice to bo back and make changes or send the notifications.
5.  **Email Notification:** The application will email each employee with only their own ranking.
6.  **Confirmation:** The application will confirm to the user that the emails have been sent successfully, and that all user submitted information has now been purged from memory and databases.

## Development Plan
1.  **Project Setup:** (Completed)
    *   Initialize a `git` repository.
    *   Create a `.gitignore` file.
    *   Set up a virtual environment using `uv`.
    *   Install Django.
    *   Initialize a new Django project and a `core` app.

2.  **Core Models and Logic:** (Completed)
    *   Developed modules for parsing the uploaded Excel files (`parser.py` for `parse_hours_report` and `parse_roster`).
    *   Implemented the ranking logic in `ranking.py` with `rank_employees` function.
    *   Employees with 0 FTE are treated as 1e-9 to avoid division by zero errors.
    *   Ranking calculated by dividing hours by FTE, with dense ranking method.

3.  **Upload and Verification Workflow:** (Completed)
    *   ✅ `UploadForm` created in `forms.py` with file uploads, assignment input, and custom message field.
    *   ✅ `upload_view` implemented to handle form submission and create ranked data.
    *   ✅ `verification_view` created to display ranked list.
    *   ✅ Verification page template (`verification.html`) created with employee ranking table and flagging for 0-hour employees.
    *   ✅ URL routing updated to include `/verification/` and `/send/` endpoints.
    *   ✅ `send_emails_view` placeholder created to prepare for email sending.

4.  **Email Notification System:** (Completed)
    *   ✅ Created `MailgunService` class in `core/services/email.py` for API integration.
    *   ✅ `send_emails_view` implemented to send personalized emails to each employee.
    *   ✅ Email template populated with employee ranking info and custom message.
    *   ✅ Session data cleared after emails are sent for privacy compliance.
    *   ✅ Mailgun API credentials configured via environment variables in settings.py.

5.  **Final Steps:** (Completed)
    *   ✅ Confirmation page implemented (`confirmation.html` template and `confirmation_view`).
    *   ✅ All user-uploaded data is cleared from session after email notification.
    *   ✅ Cloudflare Turnstile bot detection integrated on the upload form (`turnstile.py` service, custom widget, form validation).
    *   ✅ Comprehensive `README.md` written with deployment instructions for GCP, API key setup, Nginx/Gunicorn configuration, and usage guide for non-technical users.

## Project Completion Status

🎉 **PROJECT COMPLETE AND READY FOR PRODUCTION**

All development tasks have been completed successfully. The application is fully functional and ready to be deployed. 

### What Has Been Built

**Core Features:**
- ✅ File upload and parsing (Excel import for hours and employee data)
- ✅ Automatic employee ranking by hours/FTE
- ✅ Multi-step workflow: Upload → Verify → Send → Confirm
- ✅ Personalized email notifications via Mailgun
- ✅ Bot detection via Cloudflare Turnstile
- ✅ Complete data privacy (all user data deleted after email send)

**User Interfaces:**
- ✅ Upload form with file inputs and custom message area
- ✅ Verification page showing ranked employees with flagging for 0-hour workers
- ✅ Confirmation page with email delivery summary
- ✅ Responsive HTML templates with styling

**Infrastructure & Documentation:**
- ✅ Complete README with deployment guide for non-technical users
- ✅ Environment-based configuration for API keys
- ✅ Error handling and logging throughout
- ✅ Session-based workflow management

### Deployment Checklist

Before going live, ensure:

1. **Create Mailgun account** and note API key + domain
2. **Create Cloudflare account** and set up Turnstile site
3. **Provision GCP VM** (e2-micro free tier recommended)
4. **Set environment variables** in `.env` file
5. **Configure Nginx** and obtain SSL certificate
6. **Start Gunicorn service** and test locally
7. **Point domain** to your GCP VM IP
8. **Test end-to-end** with sample Excel files

See `README.md` for detailed step-by-step deployment instructions.

## Recent Progress

- Fixed local Turnstile configuration loading so `.env.local` is read before Turnstile settings are evaluated.
- Fixed the upload page Turnstile widget so successful verification writes the token into the hidden form field expected by Django validation.
- Added Turnstile form tests covering the required-token and valid-token submission paths.
- Re-enabled Django CSRF protection and restricted the email-send endpoint to `POST`.
- Hardened Django production settings for secure cookies, HTTPS redirect, HSTS, and fail-closed secret/host configuration.
- Added upload validation for spreadsheet type and size, plus session cleanup for abandoned workflows.
