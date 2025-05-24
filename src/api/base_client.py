import logging
import os
from typing import Dict, Any, Optional

import requests
from dotenv import load_dotenv

from .exceptions import (
    KeapAPIError,
    KeapAuthenticationError,
    KeapRateLimitError,
    KeapNotFoundError,
    KeapServerError
)
from ..utils.retry import exponential_backoff

# Get logger for this module
logger = logging.getLogger(__name__)

load_dotenv()


class KeapBaseClient:
    def __init__(self):
        self.base_url = "https://api.keap.com/crm/rest/v1"
        self.api_key = os.getenv('KEAP_API_KEY')
        if not self.api_key:
            raise KeapAuthenticationError("KEAP_API_KEY environment variable is not set")

        self.headers = {
            'Accept': 'application/json',
            'X-Keap-API-Key': self.api_key
        }

        # Initialize session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        logger.info("KeapBaseClient initialized")
        logger.info(f"Using base URL: {self.base_url}")

    def _handle_response(self, response: requests.Response) -> Dict:
        """
        Handle API response and raise appropriate exceptions
        
        Args:
            response: Response object from requests
            
        Returns:
            Dict containing the API response
            
        Raises:
            KeapAPIError: Base exception for API errors
            KeapAuthenticationError: Authentication issues
            KeapRateLimitError: Rate limit exceeded
            KeapNotFoundError: Resource not found
            KeapServerError: Server errors
        """
        try:
            response.raise_for_status()
            data = response.json()
            logger.debug(f"API Response: {data}")
            
            # Log quota-related headers
            quota_headers = {
                'x-keap-product-quota-limit': response.headers.get('x-keap-product-quota-limit'),
                'x-keap-product-quota-time-unit': response.headers.get('x-keap-product-quota-time-unit'),
                'x-keap-product-quota-interval': response.headers.get('x-keap-product-quota-interval'),
                'x-keap-product-quota-available': response.headers.get('x-keap-product-quota-available'),
                'x-keap-product-quota-used': response.headers.get('x-keap-product-quota-used'),
                'x-keap-product-quota-expiry-time': response.headers.get('x-keap-product-quota-expiry-time')
            }
            logger.debug("Quota Headers: %s", quota_headers)
            
            return data
        except requests.exceptions.HTTPError as e:
            status_code = response.status_code
            logger.error(f"HTTP Error: {status_code} - {str(e)}")
            logger.error(f"Response content: {response.text}")

            if status_code == 401:
                raise KeapAuthenticationError("Invalid API key or authentication failed")
            elif status_code == 404:
                raise KeapNotFoundError(f"Resource not found: {response.url}")
            elif status_code == 429:
                # Extract retry-after header if available
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    try:
                        retry_after = int(retry_after)
                    except ValueError:
                        retry_after = None
                raise KeapRateLimitError(
                    f"Rate limit exceeded. Retry after: {retry_after} seconds"
                )
            elif status_code >= 500:
                raise KeapServerError(f"Server error: {str(e)}")
            else:
                raise KeapAPIError(f"API request failed: {str(e)}")
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"JSON Decode Error: {str(e)}")
            logger.error(f"Response content: {response.text}")
            raise KeapAPIError(f"Failed to parse JSON response: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error: {str(e)}")
            raise KeapAPIError(f"Request failed: {str(e)}")

    @exponential_backoff(
        max_retries=5,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
        exceptions=(KeapRateLimitError, KeapServerError)
    )
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        """
        Make an HTTP request to the Keap API with retry logic for rate limits
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Dict containing the API response
            
        Raises:
            KeapAPIError: If the request fails after all retries
        """
        url = f"{self.base_url}/{endpoint}"

        try:
            logger.debug(f"Making {method} request to {url}")
            response = self.session.request(
                method=method,
                url=url,
                params=params
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        """
        Make a GET request to the Keap API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Dict containing the API response
            
        Raises:
            KeapAPIError: If the request fails after all retries
        """
        return self._make_request('GET', endpoint, params)

    def __del__(self):
        """Cleanup session on object destruction"""
        if hasattr(self, 'session'):
            self.session.close()
