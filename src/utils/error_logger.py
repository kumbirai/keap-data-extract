import json
import logging
import os
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)


class ErrorLogger:
    def __init__(self, error_log_dir: str = 'logs/errors'):
        """Initialize the error logger.
        
        Args:
            error_log_dir: Directory to store error logs
        """
        self.error_log_dir = error_log_dir
        os.makedirs(error_log_dir, exist_ok=True)
        self.current_log_file = self._get_log_file_path()
        logger.info(f"Error logger initialized. Log file: {self.current_log_file}")

    def _get_log_file_path(self) -> str:
        """Get the path for today's error log file."""
        date_str = datetime.now().strftime('%Y%m%d')
        return os.path.join(self.error_log_dir, f'data_load_errors_{date_str}.json')

    def _format_error_entry(self, entity_type: str, entity_id: int, error_type: str, error_message: str, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format an error entry with all relevant information.
        
        Args:
            entity_type: Type of entity (e.g., 'contact', 'tag')
            entity_id: ID of the entity that caused the error
            error_type: Type of error (e.g., 'ValidationError', 'DatabaseError')
            error_message: Detailed error message
            additional_data: Any additional context data
            
        Returns:
            Dict containing the formatted error entry
        """
        return {'timestamp': datetime.now().isoformat(), 'entity_type': entity_type, 'entity_id': entity_id, 'error_type': error_type, 'error_message': error_message,
                'additional_data': additional_data or {}, 'stack_trace': traceback.format_exc()}

    def log_error(self, entity_type: str, entity_id: int, error_type: str, error_message: str, additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an error with structured data.
        
        Args:
            entity_type: Type of entity (e.g., 'contact', 'tag')
            entity_id: ID of the entity that caused the error
            error_type: Type of error (e.g., 'ValidationError', 'DatabaseError')
            error_message: Detailed error message
            additional_data: Any additional context data
        """
        try:
            error_entry = self._format_error_entry(entity_type=entity_type, entity_id=entity_id, error_type=error_type, error_message=error_message, additional_data=additional_data)

            # Read existing errors if file exists
            existing_errors = []
            if os.path.exists(self.current_log_file):
                with open(self.current_log_file, 'r') as f:
                    try:
                        existing_errors = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"Error reading existing error log file: {self.current_log_file}")
                        # If file is corrupted, start fresh
                        existing_errors = []

            # Append new error
            existing_errors.append(error_entry)

            # Write back to file with pretty printing using custom encoder
            with open(self.current_log_file, 'w') as f:
                json.dump(existing_errors, f, indent=2, cls=CustomJSONEncoder)

            # Log to console for immediate visibility
            logger.error(f"Error processing {entity_type} {entity_id}: {error_message}\n"
                         f"Type: {error_type}\n"
                         f"Additional Data: {json.dumps(additional_data or {}, indent=2, cls=CustomJSONEncoder)}")

        except Exception as e:
            logger.error(f"Failed to write to error log file: {str(e)}")
            # Log the original error to console as fallback
            logger.error(f"Original error - Entity: {entity_type} {entity_id}, "
                         f"Type: {error_type}, Message: {error_message}")

    def get_errors(self, entity_type: Optional[str] = None) -> list:
        """Retrieve all errors or filter by entity type.
        
        Args:
            entity_type: Optional entity type to filter errors
            
        Returns:
            List of error entries
        """
        try:
            if os.path.exists(self.current_log_file):
                with open(self.current_log_file, 'r') as f:
                    errors = json.load(f)
                    if entity_type:
                        return [e for e in errors if e['entity_type'] == entity_type]
                    return errors
        except Exception as e:
            logger.error(f"Failed to read error log file: {str(e)}")
        return []

    def clear_errors(self) -> None:
        """Clear all error logs."""
        try:
            if os.path.exists(self.current_log_file):
                os.remove(self.current_log_file)
                logger.info(f"Cleared error log file: {self.current_log_file}")
        except Exception as e:
            logger.error(f"Failed to clear error log file: {str(e)}")
