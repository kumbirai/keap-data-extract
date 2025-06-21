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
from src.scripts.load_data import (load_contact_by_id, load_product_by_id, load_affiliate_by_id, load_order_by_id, load_opportunity_by_id, load_task_by_id, load_note_by_id, load_campaign_by_id)
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

        # Initialize logging
        initialize_loggers()

        # Mapping of entity types to their load functions
        self.load_functions = {'contacts': load_contact_by_id, 'products': load_product_by_id, 'affiliates': load_affiliate_by_id, 'orders': load_order_by_id, 'opportunities': load_opportunity_by_id,
            'tasks': load_task_by_id, 'notes': load_note_by_id, 'campaigns': load_campaign_by_id, }

        # Custom load functions for entities that don't have individual ID loaders
        self.custom_load_functions = {'subscriptions': self.load_subscription_by_id, }

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

    def load_subscription_by_id(self, client: KeapClient, db_session, subscription_id: int) -> bool:
        """Load a single subscription by ID from the subscriptions list."""
        try:
            logger.info(f"Loading subscription ID: {subscription_id}")

            # Get all subscriptions and filter for the specific ID
            subscriptions, _ = client.get_subscriptions()

            # Find the specific subscription
            target_subscription = None
            for subscription in subscriptions:
                if subscription.id == subscription_id:
                    target_subscription = subscription
                    break

            if not target_subscription:
                logger.warning(f"Subscription ID {subscription_id} not found in API response")
                return False

            # Use merge to handle both inserts and updates
            db_session.merge(target_subscription)
            db_session.commit()

            logger.info(f"Successfully processed subscription ID: {subscription_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing subscription ID {subscription_id}: {e}")
            db_session.rollback()
            return False

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
        """Attempt to reprocess a single entity."""
        try:
            logger.info(f"Attempting to reprocess {entity_type} ID: {entity_id}")

            # Check if we have a regular load function
            if entity_type in self.load_functions:
                load_function = self.load_functions[entity_type]
                success = load_function(self.client, self.db, entity_id)
            # Check if we have a custom load function
            elif entity_type in self.custom_load_functions:
                load_function = self.custom_load_functions[entity_type]
                success = load_function(self.client, self.db, entity_id)
            else:
                logger.warning(f"No load function available for entity type: {entity_type}")
                return False

            if success:
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

        try:
            # Load all error files
            error_files = self.load_error_files()
            if not error_files:
                logger.warning("No error files found")
                return

            # Process each error file
            all_errors = []
            for file_path in error_files:
                errors = self.parse_error_log(file_path)
                all_errors.extend(errors)

            logger.info(f"Total errors to analyze: {len(all_errors)}")

            # Extract missing dependencies from all errors
            for error_entry in all_errors:
                self.extract_missing_dependencies(error_entry)

            # Log missing dependencies summary
            for entity_type, missing_ids in self.stats['missing_dependencies'].items():
                logger.info(f"Missing {entity_type}: {len(missing_ids)} entities")

            # Reprocess missing dependencies first
            self.reprocess_missing_dependencies()

            # Then reprocess failed entities
            self.reprocess_failed_entities(all_errors)

            # Print final statistics
            self.print_statistics()

        except Exception as e:
            logger.error(f"Error during reprocessing: {e}")
            raise
        finally:
            self.db.close()

    def print_statistics(self) -> None:
        """Print final reprocessing statistics."""
        logger.info("=" * 50)
        logger.info("REPROCESSING STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total errors analyzed: {self.stats['total_errors']}")
        logger.info(f"Errors processed: {self.stats['processed_errors']}")
        logger.info(f"Successful reprocesses: {self.stats['successful_reprocesses']}")
        logger.info(f"Failed reprocesses: {self.stats['failed_reprocesses']}")

        logger.info("\nMissing dependencies found:")
        for entity_type, missing_ids in self.stats['missing_dependencies'].items():
            logger.info(f"  {entity_type}: {len(missing_ids)} entities")

        logger.info("\nSuccessfully reprocessed entities:")
        for entity_type, processed_ids in self.stats['processed_entities'].items():
            logger.info(f"  {entity_type}: {len(processed_ids)} entities")

        logger.info("=" * 50)


def main():
    """Main function to run the error reprocessor."""
    reprocessor = ErrorReprocessor()
    reprocessor.run()


if __name__ == "__main__":
    main()
