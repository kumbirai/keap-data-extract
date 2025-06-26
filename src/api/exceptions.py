from typing import Dict


class KeapAPIError(Exception):
    """Base exception for Keap API errors"""
    pass


class KeapAuthenticationError(KeapAPIError):
    """Raised when there are authentication issues"""
    pass


class KeapValidationError(KeapAPIError):
    """Raised when input validation fails"""
    pass


class KeapRateLimitError(KeapAPIError):
    """Raised when rate limit is exceeded"""

    def __init__(self, message: str, response_headers: Dict[str, str] = None):
        super().__init__(message)
        self.response_headers = response_headers or {}


class KeapNotFoundError(KeapAPIError):
    """Raised when a resource is not found"""
    pass


class KeapServerError(KeapAPIError):
    """Raised when the Keap server returns an error"""
    pass


class KeapQuotaExhaustedError(KeapAPIError):
    """Raised when the daily API quota is exhausted"""
    pass
