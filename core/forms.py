from django import forms
from django.conf import settings

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
