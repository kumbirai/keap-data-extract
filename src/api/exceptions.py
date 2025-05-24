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
    pass


class KeapNotFoundError(KeapAPIError):
    """Raised when a resource is not found"""
    pass


class KeapServerError(KeapAPIError):
    """Raised when the Keap server returns an error"""
    pass
