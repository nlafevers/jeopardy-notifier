import requests
from typing import List, Dict
from django.conf import settings


class MailgunService:
    """Service for sending emails via Mailgun API."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'MAILGUN_API_KEY', '')
        self.domain = getattr(settings, 'MAILGUN_DOMAIN', '')
        self.base_url = f'https://api.mailgun.net/v3/{self.domain}'
    
    def send_email(self, to_email: str, subject: str, text: str, from_email: str = None) -> bool:
        """
        Send a single email via Mailgun.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            text: Email body (plain text)
            from_email: Sender email address (defaults to MAILGUN_FROM_EMAIL setting)
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if from_email is None:
            from_email = getattr(settings, 'MAILGUN_FROM_EMAIL', 'no-reply@example.com')
        
        if not self.api_key or not self.domain:
            raise ValueError("Mailgun API key and domain must be configured in settings")
        
        try:
            response = requests.post(
                f'{self.base_url}/messages',
                auth=('api', self.api_key),
                data={
                    'from': from_email,
                    'to': to_email,
                    'subject': subject,
                    'text': text,
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def send_batch_emails(self, recipients: List[Dict[str, str]], subject: str, 
                         body_template: str, from_email: str = None) -> Dict[str, bool]:
        """
        Send emails to multiple recipients with personalized content.
        
        Args:
            recipients: List of dicts with keys: email, rank, hours, fte, score
            subject: Email subject
            body_template: Email body template with placeholders
            from_email: Sender email address
            
        Returns:
            Dict mapping email addresses to send status (True/False)
        """
        results = {}
        
        for recipient in recipients:
            # Format the body with recipient-specific ranking info
            ranking_info = self._format_ranking_info(recipient)
            body = body_template.replace('<employee ranking>', ranking_info)
            
            success = self.send_email(
                recipient['email'],
                subject,
                body,
                from_email
            )
            results[recipient['email']] = success
        
        return results
    
    @staticmethod
    def _format_ranking_info(recipient: Dict) -> str:
        """Format employee ranking information for email."""
        return (
            f"Your Ranking: {recipient.get('rank', 'N/A')}\n"
            f"Hours Worked: {recipient.get('hours', 0):.2f}\n"
            f"FTE: {recipient.get('fte', 1)}\n"
            f"Score (Hours/FTE): {recipient.get('score', 0):.2f}"
        )
