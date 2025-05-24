import re
from typing import Any, Dict

from .exceptions import KeapValidationError


def validate_email(email: str) -> None:
    """Validate email format"""
    if not email:
        raise KeapValidationError("Email cannot be empty")

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise KeapValidationError(f"Invalid email format: {email}")


def validate_pagination_params(limit: int, offset: int) -> None:
    """Validate pagination parameters"""
    if limit < 1:
        raise KeapValidationError("Limit must be greater than 0")
    if limit > 1000:
        raise KeapValidationError("Limit cannot exceed 1000")
    if offset < 0:
        raise KeapValidationError("Offset cannot be negative")


def validate_id(id_value: int, entity_name: str) -> None:
    """Validate ID values"""
    if not isinstance(id_value, int):
        raise KeapValidationError(f"{entity_name} ID must be an integer")
    if id_value < 1:
        raise KeapValidationError(f"{entity_name} ID must be greater than 0")


def validate_contact_data(data: Dict[str, Any]) -> None:
    """Validate contact data"""
    required_fields = ['email', 'first_name', 'last_name']
    for field in required_fields:
        if field not in data or not data[field]:
            raise KeapValidationError(f"Missing required field: {field}")

    if 'email' in data:
        validate_email(data['email'])


def validate_opportunity_data(data: Dict[str, Any]) -> None:
    """Validate opportunity data"""
    required_fields = ['title', 'contact_id', 'stage']
    for field in required_fields:
        if field not in data or not data[field]:
            raise KeapValidationError(f"Missing required field: {field}")

    if 'value' in data and not isinstance(data['value'], (int, float)):
        raise KeapValidationError("Value must be a number")

    if 'probability' in data:
        if not isinstance(data['probability'], int):
            raise KeapValidationError("Probability must be an integer")
        if not 0 <= data['probability'] <= 100:
            raise KeapValidationError("Probability must be between 0 and 100")
