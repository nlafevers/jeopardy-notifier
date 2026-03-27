from django import forms
from django.conf import settings


MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_SPREADSHEET_EXTENSIONS = {'.xlsx', '.xls', '.xlsm'}


class TurnstileWidget(forms.Widget):
    """Widget for Cloudflare Turnstile bot detection."""
    
    template_name = 'core/widgets/turnstile.html'
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['turnstile_site_key'] = getattr(settings, 'TURNSTILE_SITE_KEY', '')
        return context


class UploadForm(forms.Form):
    hours_report = forms.FileField(label='Hours Report')
    roster = forms.FileField(label='Employee Roster')
    assignment = forms.CharField(label='Assignment to Rank', initial='Jeopardy 7a-7a')
    custom_message = forms.CharField(
        label='Message',
        widget=forms.Textarea,
        required=False,
        initial='We have some unfilled jeopardy shifts in the next few weeks, please login to Qgenda and consider signing up if you are available.'
    )
    turnstile_response = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        label='Verification'
    )

    def _validate_spreadsheet_upload(self, file, field_label: str):
        if not file:
            return file

        file_name = getattr(file, 'name', '')
        lower_name = file_name.lower()
        if not any(lower_name.endswith(extension) for extension in ALLOWED_SPREADSHEET_EXTENSIONS):
            raise forms.ValidationError(f'{field_label} must be an Excel spreadsheet (.xlsx, .xls, or .xlsm).')

        if file.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(f'{field_label} must be 5 MB or smaller.')

        return file

    def clean_hours_report(self):
        return self._validate_spreadsheet_upload(self.cleaned_data.get('hours_report'), 'Hours Report')

    def clean_roster(self):
        return self._validate_spreadsheet_upload(self.cleaned_data.get('roster'), 'Employee Roster')
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check Turnstile verification if enabled
        if getattr(settings, 'REQUIRE_TURNSTILE', False):
            turnstile_response = cleaned_data.get('turnstile_response')
            if not turnstile_response:
                raise forms.ValidationError('Please verify that you are human.')
            
            # Verify with Cloudflare
            from .services.turnstile import verify_turnstile_token
            secret_key = getattr(settings, 'TURNSTILE_SECRET_KEY', '')
            
            if not verify_turnstile_token(turnstile_response, secret_key):
                raise forms.ValidationError('Verification failed. Please try again.')
        
        return cleaned_data
