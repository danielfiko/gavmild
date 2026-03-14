import os
import time
import requests
from threading import Lock

from app.utils import read_secret


class PrisjaktClient:
    """
    Client for interacting with the Prisjakt API.
    
    Usage:
        client = PrisjaktClient()
        response = client.get_product("123456")
        if response.status_code == 200:
            data = response.json()
            # Do something with data
    """
    def __init__(self):
        self.client_id = os.getenv("PRISJAKT_CLIENT_ID") #TODO: Sentralisere uthenting av dette?
        self.client_secret = read_secret("prisjakt-secret")
        self.token_url = "https://api.prisjakt.no/v1/auth/token"
        self.base_api_url = "https://api.prisjakt.no/v1/products"
        
        self.access_token = None
        self.expiration_time = 0
        self._lock = Lock()

    def _get_valid_token(self) -> str:
        with self._lock:
            if self.access_token and self.expiration_time - int(time.time()) > 60:
                return self.access_token
                
            response = requests.post(
                self.token_url,
                data={
                    'grant_type': 'client_credentials',
                    "scope": "client",
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                }
            )
            response.raise_for_status() # Automatically raises HTTP errors
            
            data = response.json()
            self.access_token = data['access_token']
            self.expiration_time = int(time.time()) + data['expires_in']
            return self.access_token

    def get_product(self, product_number: str) -> requests.Response:
        token = self._get_valid_token()
        headers = {'Authorization': f'Bearer {token}'}
        return requests.get(f"{self.base_api_url}/{product_number}", headers=headers)


# Maintain backward compatibility for API imports
_default_client: 'PrisjaktClient | None' = None

def make_request(product_number: str) -> requests.Response:
    """Legacy wrapper for backward compatibility with existing code."""
    global _default_client
    if _default_client is None:
        _default_client = PrisjaktClient()
    return _default_client.get_product(product_number)
