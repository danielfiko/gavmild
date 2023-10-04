import time
import requests


def read_secret(secret_name):
    try:
        with open(f"/run/secrets/{secret_name}", "r") as secret_file:
            return secret_file.read().strip()
    except IOError:
        return None

client_id = read_secret("prisjakt-id")
client_secret = read_secret("prisjakt-secret")
token_url = "https://api.prisjakt.no/v1/auth/token"
api_url = "https://api.prisjakt.no/v1/products/"

access_token = None
expiration_time = 0

def get_access_token(client_id, client_secret, token_url):
    """
    Get OAuth 2.0 access token and its expiration time.
    
    Args:
        client_id (str): Client ID for OAuth 2.0 authentication.
        client_secret (str): Client secret for OAuth 2.0 authentication.
        token_url (str): URL to obtain OAuth 2.0 access token.
        
    Returns:
        str: OAuth 2.0 access token.
        int: Expiration timestamp of the access token.
    """
    response = requests.post(
        token_url,
        data={
            'grant_type': 'client_credentials',
            "scope": "client",
            'client_id': client_id,
            'client_secret': client_secret
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        access_token = data['access_token']
        expires_in = data['expires_in']
        expiration_time = int(time.time()) + expires_in  # Calculate expiration timestamp
        return access_token, expiration_time
    else:
        data = response.json()
        raise Exception("Failed to obtain access token: " + str(data))

def make_api_call(api_url, access_token):
    """
    Make an API call using the provided OAuth 2.0 access token.
    
    Args:
        api_url (str): URL of the API endpoint to call.
        access_token (str): OAuth 2.0 access token.
        
    Returns:
        requests.Response: Response object from the API call.
    """
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(api_url, headers=headers)
    return response

def get_authenticated_response(client_id, client_secret, token_url, api_url):
    """
    Get an authenticated API response by managing OAuth 2.0 token expiration.
    
    Args:
        client_id (str): Client ID for OAuth 2.0 authentication.
        client_secret (str): Client secret for OAuth 2.0 authentication.
        token_url (str): URL to obtain OAuth 2.0 access token.
        api_url (str): URL of the API endpoint to call.
        
    Returns:
        requests.Response: Authenticated API response.
    """
    #access_token, expiration_time = get_access_token(client_id, client_secret, token_url)

    global expiration_time, access_token
    
    # Check if the token is expired or about to expire (within the next minute)
    if expiration_time - int(time.time()) <= 60 or not access_token:
        # Refresh the token if it's expired or about to expire
        access_token, expiration_time = get_access_token(client_id, client_secret, token_url)
    
    # Make the API call using the refreshed access token
    response = make_api_call(api_url, access_token)
    return response

def make_request(product_number):
    response = get_authenticated_response(client_id, client_secret, token_url, api_url + product_number)
    return response