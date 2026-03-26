from django.shortcuts import render, redirect
from django.conf import settings
from .forms import UploadForm
from .services.parser import parse_hours_report, parse_roster
from .services.ranking import rank_employees
from .services.email import MailgunService
import pandas as pd
from io import StringIO

def upload_view(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            hours_report_file = form.cleaned_data['hours_report']
            roster_file = form.cleaned_data['roster']
            assignment = form.cleaned_data['assignment']
            
            hours_df = parse_hours_report(hours_report_file)
            roster_df = parse_roster(roster_file)
            
            ranked_df = rank_employees(hours_df, roster_df, assignment)
            
            # Store ranked data in session
            request.session['ranked_data'] = ranked_df.to_json(orient='split')
            request.session['custom_message'] = form.cleaned_data['custom_message']
            
            return redirect('verification')
    else:
        form = UploadForm()
    
    context = {
        'form': form,
        'turnstile_site_key': getattr(settings, 'TURNSTILE_SITE_KEY', '')
    }
    return render(request, 'core/upload.html', context)

def verification_view(request):
    ranked_data_json = request.session.get('ranked_data')
    if not ranked_data_json:
        return redirect('upload')
        
    ranked_df = pd.read_json(StringIO(ranked_data_json), orient='split')
    
    # Get employees with 0 hours who were not in the original report
    # (this requires more info than is currently passed)
    # For now, just flagging those with 0 hours.
    flagged_employees = ranked_df[ranked_df['Hours'] == 0]
    
    context = {
        'ranked_employees': ranked_df.to_dict('records'),
        'flagged_employees': flagged_employees.to_dict('records')
    }
    
    return render(request, 'core/verification.html', context)

def send_emails_view(request):
    """Send notification emails to all ranked employees."""
    ranked_data_json = request.session.get('ranked_data')
    if not ranked_data_json:
        return redirect('upload')
    
    ranked_df = pd.read_json(StringIO(ranked_data_json), orient='split')
    custom_message = request.session.get('custom_message', '')
    
    # Prepare email template body
    email_template = (
        "Hello {first_name},\n\n"
        "We have some unfilled jeopardy shifts in the next few weeks, please login to Qgenda and consider signing up if you are available. "
        "Please find below your current ranking:\n\n"
        "<employee ranking>\n"
    )
    
    if custom_message:
        email_template += f"\n{custom_message}\n"
    
    email_template += "\nThanks,\nMCH Hospital Medicine"
    
    # Send emails via Mailgun
    mailgun = MailgunService()
    email_count = 0
    
    try:
        for _, employee in ranked_df.iterrows():
            # Get email address - check both 'Email' and 'email' columns
            email = employee.get('Email') or employee.get('email')
            if not email:
                continue
            
            # Format employee name
            first_name = employee.get('First', employee.get('first_name', 'Employee'))
            
            # Format ranking info
            ranking_info = (
                f"Your Ranking: {int(employee.get('Rank', 0))}\n"
                f"Hours Worked: {float(employee.get('Hours', 0)):.2f}\n"
                f"FTE: {float(employee.get('FTE', 1))}\n"
                f"Score (Hours/FTE): {float(employee.get('Score', 0)):.2f}"
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
    except Exception as e:
        print(f"Error sending emails: {str(e)}")
        # Continue to confirmation anyway - emails may have been partially sent
    
    # Store email count in session for confirmation page
    request.session['email_count'] = email_count
    
    # Clear sensitive data from session
    del request.session['ranked_data']
    del request.session['custom_message']
    
    return redirect('confirmation')

def confirmation_view(request):
    """Show confirmation that emails have been sent and data has been cleared."""
    email_count = request.session.get('email_count', 0)
    
    # Clear session after displaying
    request.session.flush()
    
    context = {
        'email_count': email_count
    }
    
    return render(request, 'core/confirmation.html', context)
