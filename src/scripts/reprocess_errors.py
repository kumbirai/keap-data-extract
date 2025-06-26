#!/usr/bin/env python3
"""
Script to reprocess entities that failed during the load process.

This script reads error logs from the logs/errors/ directory and attempts to reprocess
entities that failed due to missing dependencies (like foreign key violations).
"""

import glob
import json
import logging
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.scripts.load_data import DataLoadManager
from src.utils.global_logger import initialize_loggers
from src.utils.logging_config import setup_logging

# Setup logging
setup_logging(log_level=logging.INFO, log_dir="logs", app_name="keap_data_extract")
logger = logging.getLogger(__name__)


class ErrorReprocessor:
    """Class to handle reprocessing of failed entities from error logs."""

    def __init__(self):
        self.client = KeapClient()
        self.db = SessionLocal()
        self.errors_dir = "logs/errors"
        self.data_load_manager = DataLoadManager()

        # Initialize logging
        initialize_loggers()

        # Statistics
        self.stats = {'total_errors': 0, 'processed_errors': 0, 'successful_reprocesses': 0, 'failed_reprocesses': 0, 'missing_dependencies': defaultdict(set), 'processed_entities': defaultdict(set)}

    def load_error_files(self) -> List[str]:
        """Load all error log files from the errors directory."""
        pattern = os.path.join(self.errors_dir, "data_load_errors_*.json")
        error_files = glob.glob(pattern)
        logger.info(f"Found {len(error_files)} error log files")
        return error_files

    def parse_error_log(self, file_path: str) -> List[Dict]:
        """Parse a single error log file and return list of error entries."""
        try:
            with open(file_path, 'r') as f:
                errors = json.load(f)
            logger.info(f"Loaded {len(errors)} errors from {file_path}")
            return errors
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []

    def extract_missing_dependencies(self, error_entry: Dict) -> List[Tuple[str, int]]:
        """
        Extract missing dependencies from error stack trace.
        
        Returns list of tuples: (entity_type, entity_id)
        """
        missing_deps = []
        stack_trace = error_entry.get('stack_trace', '')

        # Look for foreign key violation patterns
        # Pattern: Key (contact_id)=(1813) is not present in table "contacts"
        fk_pattern = r'Key \((\w+)\)=\((\d+)\) is not present in table "(\w+)"'
        matches = re.findall(fk_pattern, stack_trace)

        for field_name, entity_id, table_name in matches:
            # Map table names to entity types
            table_to_entity = {'contacts': 'contacts', 'products': 'products', 'affiliates': 'affiliates', 'orders': 'orders', 'opportunities': 'opportunities', 'tasks': 'tasks', 'notes': 'notes',
                               'campaigns': 'campaigns', }

            entity_type = table_to_entity.get(table_name)
            if entity_type:
                missing_deps.append((entity_type, int(entity_id)))
                self.stats['missing_dependencies'][entity_type].add(int(entity_id))

        return missing_deps

    def should_reprocess_entity(self, error_entry: Dict) -> bool:
        """Determine if an entity should be reprocessed based on error type."""
        error_type = error_entry.get('error_type', '')
        entity_type = error_entry.get('entity_type', '')

        # Only reprocess entities that failed due to foreign key violations
        # and are not the entity type that's missing dependencies
        if error_type == 'IntegrityError' and 'ForeignKeyViolation' in error_entry.get('error_message', ''):
            return True

        return False

    def reprocess_entity(self, entity_type: str, entity_id: int) -> bool:
        """Attempt to reprocess a single entity using the new DataLoadManager."""
        try:
            logger.info(f"Attempting to reprocess {entity_type} ID: {entity_id}")

            # Use the DataLoadManager to load the specific entity
            result = self.data_load_manager.load_entity(entity_type, entity_id)

            if result.success_count > 0:
                logger.info(f"Successfully reprocessed {entity_type} ID: {entity_id}")
                self.stats['successful_reprocesses'] += 1
                self.stats['processed_entities'][entity_type].add(entity_id)
                return True
            else:
                logger.warning(f"Failed to reprocess {entity_type} ID: {entity_id}")
                self.stats['failed_reprocesses'] += 1
                return False

        except Exception as e:
            logger.error(f"Error reprocessing {entity_type} ID {entity_id}: {e}")
            self.stats['failed_reprocesses'] += 1
            return False

    def reprocess_missing_dependencies(self) -> None:
        """Reprocess all missing dependencies in dependency order."""
        # Define dependency order (entities that should be loaded first)
        dependency_order = ['products',  # Load products first (subscription plans depend on them)
                            'contacts',  # Load contacts (many entities depend on them)
                            'affiliates',  # Load affiliates
                            'orders',  # Load orders
                            'opportunities',  # Load opportunities
                            'tasks',  # Load tasks
                            'notes',  # Load notes
                            'campaigns',  # Load campaigns
                            ]

        logger.info("Starting to reprocess missing dependencies...")

        for entity_type in dependency_order:
            if entity_type in self.stats['missing_dependencies']:
                missing_ids = self.stats['missing_dependencies'][entity_type]
                logger.info(f"Reprocessing {len(missing_ids)} missing {entity_type}")

                for entity_id in missing_ids:
                    self.reprocess_entity(entity_type, entity_id)

    def reprocess_failed_entities(self, errors: List[Dict]) -> None:
        """Reprocess entities that failed during the original load."""
        logger.info("Starting to reprocess failed entities...")

        for error_entry in errors:
            self.stats['total_errors'] += 1

            if not self.should_reprocess_entity(error_entry):
                continue

            entity_type = error_entry.get('entity_type')
            entity_id = error_entry.get('entity_id')

            if entity_type and entity_id:
                self.stats['processed_errors'] += 1
                self.reprocess_entity(entity_type, entity_id)

    def run(self) -> None:
        """Main method to run the error reprocessing."""
        logger.info("Starting error reprocessing...")

        # Load all error files
        error_files = self.load_error_files()
        if not error_files:
            logger.info("No error files found to reprocess")
            return

        # Process each error file
        all_errors = []
        for error_file in error_files:
            errors = self.parse_error_log(error_file)
            all_errors.extend(errors)

        if not all_errors:
            logger.info("No errors found to reprocess")
            return

        logger.info(f"Found {len(all_errors)} total errors to process")

        # Extract missing dependencies from all errors
        for error_entry in all_errors:
            self.extract_missing_dependencies(error_entry)

        # First, reprocess missing dependencies
        if any(self.stats['missing_dependencies'].values()):
            self.reprocess_missing_dependencies()

        # Then, reprocess failed entities
        self.reprocess_failed_entities(all_errors)

        # Print statistics
        self.print_statistics()

    def print_statistics(self) -> None:
        """Print reprocessing statistics."""
        logger.info("=== Error Reprocessing Statistics ===")
        logger.info(f"Total errors processed: {self.stats['total_errors']}")
        logger.info(f"Errors selected for reprocessing: {self.stats['processed_errors']}")
        logger.info(f"Successful reprocesses: {self.stats['successful_reprocesses']}")
        logger.info(f"Failed reprocesses: {self.stats['failed_reprocesses']}")

        if self.stats['missing_dependencies']:
            logger.info("Missing dependencies found:")
            for entity_type, entity_ids in self.stats['missing_dependencies'].items():
                logger.info(f"  {entity_type}: {len(entity_ids)} entities")

        if self.stats['processed_entities']:
            logger.info("Successfully reprocessed entities:")
            for entity_type, entity_ids in self.stats['processed_entities'].items():
                logger.info(f"  {entity_type}: {len(entity_ids)} entities")

        logger.info("=== End Statistics ===")

    def close(self):
        """Close database connection."""
        self.db.close()
        self.data_load_manager.close()


def main():
    """Main function to run error reprocessing."""
    reprocessor = ErrorReprocessor()
    try:
        reprocessor.run()
    finally:
        reprocessor.close()


if __name__ == "__main__":
    main()
