import logging
import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from .exceptions import (KeapAPIError, KeapAuthenticationError, KeapNotFoundError, KeapQuotaExhaustedError, KeapRateLimitError, KeapServerError)
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

        self.headers = {'Accept': 'application/json', 'X-Keap-API-Key': self.api_key}

        # Initialize session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        logger.info("KeapBaseClient initialized")
        logger.info(f"Using base URL: {self.base_url}")

    @staticmethod
    def safe_int_parse(value, default=0):
        """Safely parse an integer value, handling empty, None, and whitespace-only strings"""
        if not value or str(value).strip() == '':
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def has_meaningful_value(value):
        """Check if a header value is meaningful (not empty, None, or whitespace-only)"""
        return value is not None and str(value).strip() != ''

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
        # Log quota and throttle headers at the start since we need them in both success and error cases
        quota_headers = {'x-keap-product-quota-limit': response.headers.get('x-keap-product-quota-limit'), 'x-keap-product-quota-time-unit': response.headers.get('x-keap-product-quota-time-unit'),
                         'x-keap-product-quota-interval': response.headers.get('x-keap-product-quota-interval'),
                         'x-keap-product-quota-available': response.headers.get('x-keap-product-quota-available'), 'x-keap-product-quota-used': response.headers.get('x-keap-product-quota-used'),
                         'x-keap-product-quota-expiry-time': response.headers.get('x-keap-product-quota-expiry-time')}

        throttle_headers = {'x-keap-product-throttle-limit': response.headers.get('x-keap-product-throttle-limit'),
                            'x-keap-product-throttle-time-unit': response.headers.get('x-keap-product-throttle-time-unit'),
                            'x-keap-product-throttle-interval': response.headers.get('x-keap-product-throttle-interval'),
                            'x-keap-product-throttle-available': response.headers.get('x-keap-product-throttle-available'),
                            'x-keap-product-throttle-used': response.headers.get('x-keap-product-throttle-used')}

        tenant_headers = {'x-keap-tenant-id': response.headers.get('x-keap-tenant-id'), 'x-keap-tenant-throttle-limit': response.headers.get('x-keap-tenant-throttle-limit'),
                          'x-keap-tenant-throttle-time-unit': response.headers.get('x-keap-tenant-throttle-time-unit'),
                          'x-keap-tenant-throttle-interval': response.headers.get('x-keap-tenant-throttle-interval'),
                          'x-keap-tenant-throttle-available': response.headers.get('x-keap-tenant-throttle-available'),
                          'x-keap-tenant-throttle-used': response.headers.get('x-keap-tenant-throttle-used')}

        logger.debug("Quota Headers: %s", quota_headers)
        logger.debug("Throttle Headers: %s", throttle_headers)
        logger.debug("Tenant Headers: %s", tenant_headers)

        # Log raw header values for debugging
        logger.debug("Raw quota available header: %r", response.headers.get('x-keap-product-quota-available'))
        logger.debug("Raw throttle available header: %r", response.headers.get('x-keap-product-throttle-available'))
        logger.debug("Raw tenant available header: %r", response.headers.get('x-keap-tenant-throttle-available'))

        # Log all headers for debugging (only in debug mode)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("All response headers:")
            for header_name, header_value in response.headers.items():
                if 'keap' in header_name.lower():
                    logger.debug("  %s: %r", header_name, header_value)

        try:
            response.raise_for_status()
            data = response.json()
            logger.debug(f"API Response: {data}")
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
                # Log all rate limit related headers at INFO level
                logger.info("Rate limit exceeded. Headers: Quota=%s, Throttle=%s, Tenant=%s", quota_headers, throttle_headers, tenant_headers)

                # Determine if we hit product quota or throttle limits
                quota_available_raw = quota_headers.get('x-keap-product-quota-available')
                throttle_available_raw = throttle_headers.get('x-keap-product-throttle-available')
                tenant_available_raw = tenant_headers.get('x-keap-tenant-throttle-available')

                quota_available = self.safe_int_parse(quota_available_raw)
                throttle_available = self.safe_int_parse(throttle_available_raw)
                tenant_available = self.safe_int_parse(tenant_available_raw)

                logger.debug(f"Parsed values - Quota available: {quota_available}, Throttle available: {throttle_available}, Tenant available: {tenant_available}")

                # Check if we've hit the daily quota limit
                # Only trigger if we have meaningful quota data AND it's actually 0
                if self.has_meaningful_value(quota_available_raw) and quota_available == 0 and quota_headers.get('x-keap-product-quota-time-unit', '').lower() == 'day':
                    quota_limit = quota_headers.get('x-keap-product-quota-limit', 'unknown')
                    quota_used = quota_headers.get('x-keap-product-quota-used', 'unknown')
                    logger.error("Daily API quota exhausted. Quota limit: %s, Used: %s. "
                                 "Quota will reset at midnight GMT. Exiting gracefully.", quota_limit, quota_used)
                    raise KeapQuotaExhaustedError(f"Daily API quota exhausted (limit: {quota_limit}, used: {quota_used}). "
                                                  "Quota will reset at midnight GMT.")

                # If quota headers are missing or empty, but we have throttle information,
                # assume this is a throttle limit, not a quota limit
                if (quota_headers.get('x-keap-product-quota-available') is None or quota_headers.get('x-keap-product-quota-available') == '') and throttle_available == 0:
                    logger.warning("Quota headers are missing/empty, but throttle limit is hit. Treating as throttle limit.")
                    limit_type = "product throttle"
                    limit_value = self.safe_int_parse(throttle_headers.get('x-keap-product-throttle-limit'))
                elif (quota_headers.get('x-keap-product-quota-available') is None or quota_headers.get('x-keap-product-quota-available') == '') and tenant_available == 0:
                    logger.warning("Quota headers are missing/empty, but tenant throttle limit is hit. Treating as throttle limit.")
                    limit_type = "tenant throttle"
                    limit_value = self.safe_int_parse(tenant_headers.get('x-keap-tenant-throttle-limit'))
                # For throttle limits, determine which type was hit and get relevant values
                elif self.has_meaningful_value(throttle_available_raw) and throttle_available == 0:
                    limit_type = "product throttle"
                    limit_value = self.safe_int_parse(throttle_headers.get('x-keap-product-throttle-limit'))
                elif self.has_meaningful_value(tenant_available_raw) and tenant_available == 0:
                    limit_type = "tenant throttle"
                    limit_value = self.safe_int_parse(tenant_headers.get('x-keap-tenant-throttle-limit'))
                else:
                    # If we can't determine the specific limit type, use a generic message
                    limit_type = "unknown"
                    limit_value = 0

                # Combine all headers for the rate limit error
                all_headers = {**quota_headers, **throttle_headers, **tenant_headers}

                raise KeapRateLimitError(f"Rate limit exceeded ({limit_type}, limit: {limit_value}). "
                                         f"Will retry after throttle period.", response_headers=all_headers)
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

    @exponential_backoff(max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True, exceptions=(KeapRateLimitError, KeapServerError))
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
            response = self.session.request(method=method, url=url, params=params)
            logger.debug(f"Response: {response}")
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
