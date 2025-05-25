import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ErrorLogger:
    def __init__(self, error_log_dir: str = 'logs/errors'):
        self.error_log_dir = error_log_dir
        os.makedirs(error_log_dir, exist_ok=True)
        self.current_log_file = self._get_log_file_path()

    def _get_log_file_path(self) -> str:
        """Get the path for today's error log file."""
        date_str = datetime.now().strftime('%Y%m%d')
        return os.path.join(self.error_log_dir, f'data_load_errors_{date_str}.json')

    def log_error(self, 
                 entity_type: str,
                 entity_id: int,
                 error_type: str,
                 error_message: str,
                 additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error with structured data.
        
        Args:
            entity_type: Type of entity (e.g., 'contact', 'tag')
            entity_id: ID of the entity that caused the error
            error_type: Type of error (e.g., 'ValidationError', 'DatabaseError')
            error_message: Detailed error message
            additional_data: Any additional context data
        """
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'entity_type': entity_type,
            'entity_id': entity_id,
            'error_type': error_type,
            'error_message': error_message,
            'additional_data': additional_data or {}
        }

        try:
            # Read existing errors if file exists
            existing_errors = []
            if os.path.exists(self.current_log_file):
                with open(self.current_log_file, 'r') as f:
                    try:
                        existing_errors = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"Error reading existing error log file: {self.current_log_file}")

            # Append new error
            existing_errors.append(error_entry)

            # Write back to file
            with open(self.current_log_file, 'w') as f:
                json.dump(existing_errors, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to write to error log file: {str(e)}")

    def get_errors(self, entity_type: Optional[str] = None) -> list:
        """Retrieve all errors or filter by entity type."""
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