import requests
from typing import Dict


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
        return result.get('success', False)
    except Exception as e:
        print(f"Error verifying Turnstile token: {str(e)}")
        return False
