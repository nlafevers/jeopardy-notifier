import logging

import requests

logger = logging.getLogger(__name__)


def verify_turnstile_token(token: str, secret_key: str) -> bool:
    """
    Verify a Cloudflare Turnstile token.
    
    Args:
        token: The Turnstile response token from the client
        secret_key: The Turnstile secret key from settings
        
    Returns:
        True if token is valid, False otherwise
    """
    if not token or not secret_key:
        return False
    
    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': secret_key,
                'response': token,
            },
            timeout=10
        )
        
        result = response.json()
        if not result.get('success', False):
            logger.warning(
                'Turnstile verification failed',
                extra={
                    'turnstile_error_codes': result.get('error-codes', []),
                    'turnstile_hostname': result.get('hostname'),
                },
            )
        return result.get('success', False)
    except Exception as e:
        logger.exception('Error verifying Turnstile token: %s', str(e))
        return False
