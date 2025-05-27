import os
import sys
import requests
from dotenv import load_dotenv

def retrieve_access_token(silent=False):
    """
    Retrieve an access token from Adobe's authentication service.
    Uses client credentials from environment variables or .env file.
    
    Args:
        silent (bool): Whether to suppress output messages
    
    Returns:
        str: The access token for API authentication
    """
    load_dotenv()  # Load environment variables from .env file
    
    if 'FIREFLY_SERVICES_CLIENT_ID' not in os.environ or 'FIREFLY_SERVICES_CLIENT_SECRET' not in os.environ:
        print("Error: FIREFLY_SERVICES_CLIENT_ID and FIREFLY_SERVICES_CLIENT_SECRET must be set in environment variables or .env file")
        sys.exit(1)

    client_id = os.environ['FIREFLY_SERVICES_CLIENT_ID']
    client_secret = os.environ['FIREFLY_SERVICES_CLIENT_SECRET']

    token_url = 'https://ims-na1.adobelogin.com/ims/token/v3'
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis'
    }

    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    token_data = response.json()
    if not silent:
        print("Access Token Retrieved")
    return token_data['access_token'] 