from django import forms
from turnstile.fields import TurnstileField


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
    turnstile = TurnstileField()

