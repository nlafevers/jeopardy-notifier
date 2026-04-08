import logging
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from .forms import UploadForm
from .services.parser import parse_hours_report, parse_roster
from .services.ranking import rank_employees
from .services.email import MailgunService
import pandas as pd
from io import StringIO

logger = logging.getLogger(__name__)

WORKFLOW_SESSION_KEYS = (
    'ranked_data',
    'custom_message',
    'email_count',
    'human_verified',
)


def clear_workflow_session(request):
    for key in WORKFLOW_SESSION_KEYS:
        request.session.pop(key, None)


@require_GET
def health_view(_request):
    return HttpResponse('ok', content_type='text/plain')


def default_selected_names(ranked_df: pd.DataFrame) -> list[str]:
    return ranked_df.loc[~ranked_df['DoNotRank'], 'Qgenda'].astype(str).tolist()


def filter_selected_employees(ranked_df: pd.DataFrame, selected_names: list[str]) -> pd.DataFrame:
    if not selected_names:
        return ranked_df.iloc[0:0].copy()

    return ranked_df[ranked_df['Qgenda'].astype(str).isin(selected_names)].copy()


@require_http_methods(['GET', 'POST'])
def upload_view(request):
    if request.method == 'GET':
        clear_workflow_session(request)
        form = UploadForm()
    else:
        form = UploadForm(request.POST, request.FILES)
    if request.method == 'POST':
        if form.is_valid():
            hours_report_file = form.cleaned_data['hours_report']
            roster_file = form.cleaned_data['roster']
            assignment = form.cleaned_data['assignment']

            try:
                hours_df = parse_hours_report(hours_report_file)
                roster_df = parse_roster(roster_file)
                ranked_df = rank_employees(hours_df, roster_df, assignment)
            except Exception:
                logger.exception('Spreadsheet parsing failed')
                form.add_error(None, 'We could not read one or both spreadsheets. Please confirm the file format and contents.')
                context = {
                    'form': form,
                    'turnstile_site_key': getattr(settings, 'TURNSTILE_SITE_KEY', '')
                }
                return render(request, 'core/upload.html', context, status=400)

            # Store ranked data in session
            request.session['ranked_data'] = ranked_df.to_json(orient='split')
            request.session['custom_message'] = form.cleaned_data['custom_message']
            request.session['human_verified'] = True
            request.session.set_expiry(getattr(settings, 'SESSION_COOKIE_AGE', 1800))

            return redirect('verification')
    
    context = {
        'form': form,
        'turnstile_site_key': getattr(settings, 'TURNSTILE_SITE_KEY', '')
    }
    return render(request, 'core/upload.html', context)

@require_http_methods(['GET', 'POST'])
def verification_view(request):
    if getattr(settings, 'REQUIRE_TURNSTILE', False) and not request.session.get('human_verified'):
        return redirect('upload')

    ranked_data_json = request.session.get('ranked_data')
    if not ranked_data_json:
        return redirect('upload')

    ranked_df = pd.read_json(StringIO(ranked_data_json), orient='split')

    if request.method == 'POST':
        selected_names = request.POST.getlist('selected')
        action = request.POST.get('action')
        filtered_df = filter_selected_employees(ranked_df, selected_names)

        if action == 'update':
            if not filtered_df.empty:
                rankable_mask = ~filtered_df['DoNotRank']
                filtered_df = filtered_df.copy()
                filtered_df['Rank'] = filtered_df['Rank'].astype(str)

                if rankable_mask.any():
                    filtered_df.loc[rankable_mask, 'Rank'] = (
                        filtered_df.loc[rankable_mask, 'Score']
                        .rank(method='dense', ascending=False)
                        .astype(int)
                        .astype(str)
                    )

                filtered_df.loc[~rankable_mask, 'Rank'] = 'DNR'

                ranked_subset = filtered_df.loc[rankable_mask].sort_values('Score', ascending=False)
                dnr_subset = filtered_df.loc[~rankable_mask].sort_values(
                    ['Hours', 'EmailName'],
                    ascending=[False, True],
                )
                filtered_df = pd.concat([ranked_subset, dnr_subset], ignore_index=True)

            request.session['ranked_data'] = filtered_df.to_json(orient='split')
            ranked_df = filtered_df

        elif action == 'send':
            # Apply selected subset exactly as displayed, without recomputing ranking.
            request.session['ranked_data'] = filtered_df.to_json(orient='split')
            return redirect('send_emails')


    # Get employees with 0 hours who were not in the original report
    # (this requires more info than is currently passed)
    # For now, just flagging those with 0 hours.
    flagged_employees = ranked_df[(ranked_df['Hours'] == 0) | (ranked_df['DoNotRank'])]

    context = {
        'ranked_employees': ranked_df.to_dict('records'),
        'flagged_employees': flagged_employees.to_dict('records'),
        'selected_names': default_selected_names(ranked_df)
    }

    return render(request, 'core/verification.html', context)

@require_POST
def send_emails_view(request):
    """Send notification emails to all ranked employees."""
    if getattr(settings, 'REQUIRE_TURNSTILE', False) and not request.session.get('human_verified'):
        return redirect('upload')

    ranked_data_json = request.session.get('ranked_data')
    if not ranked_data_json:
        return redirect('upload')
    
    ranked_df = pd.read_json(StringIO(ranked_data_json), orient='split')
    selected_names = request.POST.getlist('selected')
    recipients_df = filter_selected_employees(ranked_df, selected_names)
    custom_message = request.session.get('custom_message', '')
    
    # Prepare email template body
    default_custom = (
        "We have some unfilled jeopardy shifts in the next few weeks, "
        "please login to Qgenda and consider signing up if you are available."
    )
    effective_message = custom_message.strip() if custom_message.strip() else default_custom

    email_template = (
        "Hello {first_name},\n\n"
        f"{effective_message}\n\n"
        "Here is your current ranking for recent jeopardy shifts worked:\n\n"
        "<employee ranking>\n"
        "\nThanks,\nMCH Hospital Medicine"
    )
    
    # Send emails via Mailgun
    mailgun = MailgunService()
    email_count = 0
    total_ranked = int((~ranked_df['DoNotRank']).sum()) if 'DoNotRank' in ranked_df.columns else len(ranked_df)
    
    try:
        for _, employee in recipients_df.iterrows():
            # Get email address - check both 'Email' and 'email' columns
            email = employee.get('Email') or employee.get('email')
            if not email:
                continue
            
            # Format employee name
            first_name = employee.get('EmailName', employee.get('first_name', 'Employee'))
            rank = employee.get('Rank', 'N/A')
            score_display = 'N/A' if employee.get('DoNotRank') else f"{float(employee.get('Score', 0)):.2f}"
            
            # Format ranking info
            ranking_info = (
                f"Your Ranking: {rank}\n"
                f"Total Ranked Employees: {total_ranked}\n"
                f"Hours Worked: {float(employee.get('Hours', 0)):.2f}\n"
                f"FTE: {float(employee.get('FTE', 1))}\n"
                f"Score (Hours/FTE): {score_display}"
            )
            
            # Create personalized email body
            body = email_template.replace('{first_name}', first_name)
            body = body.replace('<employee ranking>', ranking_info)
            
            # Send email
            success = mailgun.send_email(
                email,
                'Open Jeopardy Shifts',
                body
            )
            
            if success:
                email_count += 1
    except Exception:
        logger.exception('Unexpected error while sending emails')
        # Continue to confirmation anyway - emails may have been partially sent
    
    # Store email count in session for confirmation page
    request.session['email_count'] = email_count
    
    # Clear sensitive data from session
    request.session.pop('ranked_data', None)
    request.session.pop('custom_message', None)
    
    return redirect('confirmation')

@require_GET
def confirmation_view(request):
    """Show confirmation that emails have been sent and data has been cleared."""
    if getattr(settings, 'REQUIRE_TURNSTILE', False) and not request.session.get('human_verified'):
        return redirect('upload')

    email_count = request.session.get('email_count', 0)
    
    # Clear session after displaying
    request.session.flush()
    
    context = {
        'email_count': email_count
    }
    
    return render(request, 'core/confirmation.html', context)
