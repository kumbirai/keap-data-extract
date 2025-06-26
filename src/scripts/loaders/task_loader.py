"""
Specialized loader for tasks.

Tasks have relationships with contacts and specific attributes like priority,
status, due dates, and completion dates that need special handling.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from src.models.models import Contact
from .base_loader import BaseEntityLoader

logger = logging.getLogger(__name__)


class TaskLoader(BaseEntityLoader):
    """Specialized loader for tasks with relationship handling.
    
    Tasks are unique because:
    1. They have relationships with contacts that need to be properly linked
    2. They have priority levels (LOW, MEDIUM, HIGH, URGENT)
    3. They have status tracking (PENDING, COMPLETED, CANCELLED, etc.)
    4. They have due dates and completion dates that need validation
    5. They may have task types and notes that need processing
    """

    def __init__(self, client: KeapClient, db: Session, checkpoint_manager: Any):
        super().__init__(client, db, checkpoint_manager, "tasks", "get_tasks", "get_task")

    def _process_entity(self, task: Any) -> None:
        """Process task-specific relationships and attributes.
        
        This method handles the complex relationships and attributes that tasks have:
        - Contact relationships
        - Priority and status validation
        - Due date and completion date processing
        - Task type and notes handling
        """
        # Handle contact relationships
        if hasattr(task, 'contacts'):
            # Ensure all referenced contacts exist in the database
            self._ensure_contacts_exist(task.contacts)
            task.contacts = task.contacts

        # Handle primary contact relationship
        if hasattr(task, 'contact_id') and task.contact_id:
            self._ensure_primary_contact_exists(task.contact_id)

        # Validate and process task attributes
        self._process_task_attributes(task)

        # Handle task type and notes
        self._process_task_content(task)

    def _ensure_contacts_exist(self, contacts: list) -> None:
        """Ensure all referenced contacts exist in the database.
        
        This method checks if the contacts associated with a task
        exist in the database and logs warnings for any missing contacts.
        """
        if not contacts:
            return

        for contact in contacts:
            try:
                # Check if contact exists in database
                existing_contact = self.db.query(Contact).filter(Contact.id == contact.id).first()

                if existing_contact is None:
                    logger.warning(f"Contact ID {contact.id} referenced by task not found in database")
                else:
                    logger.debug(f"Contact ID {contact.id} exists in database")

            except Exception as e:
                logger.error(f"Error checking contact ID {contact.id}: {str(e)}")

    def _ensure_primary_contact_exists(self, contact_id: int) -> None:
        """Ensure the primary contact for a task exists in the database."""
        try:
            # Check if primary contact exists in database
            existing_contact = self.db.query(Contact).filter(Contact.id == contact_id).first()

            if existing_contact is None:
                logger.warning(f"Primary contact ID {contact_id} for task not found in database")
            else:
                logger.debug(f"Primary contact ID {contact_id} exists in database")

        except Exception as e:
            logger.error(f"Error checking primary contact ID {contact_id}: {str(e)}")

    def _process_task_attributes(self, task: Any) -> None:
        """Process and validate task-specific attributes.
        
        This method handles priority, status, due dates, and completion dates
        with appropriate validation and logging.
        """
        # Log priority information
        if hasattr(task, 'priority') and task.priority:
            logger.debug(f"Processing task {task.id} with priority: {task.priority}")

        # Log status information
        if hasattr(task, 'status') and task.status:
            logger.debug(f"Processing task {task.id} with status: {task.status}")

        # Process due date
        if hasattr(task, 'due_date') and task.due_date:
            try:
                logger.debug(f"Task {task.id} has due date: {task.due_date}")  # Could add validation here (e.g., ensure due date is in the future for pending tasks)
            except Exception as e:
                logger.warning(f"Error processing due date for task {task.id}: {str(e)}")

        # Process completion date
        if hasattr(task, 'completed_date') and task.completed_date:
            try:
                logger.debug(f"Task {task.id} was completed on: {task.completed_date}")  # Could add validation here (e.g., ensure completion date is after creation date)
            except Exception as e:
                logger.warning(f"Error processing completion date for task {task.id}: {str(e)}")

        # Validate status and completion date consistency
        self._validate_status_consistency(task)

    def _validate_status_consistency(self, task: Any) -> None:
        """Validate consistency between task status and completion date."""
        try:
            if hasattr(task, 'status') and hasattr(task, 'completed_date'):
                if task.status == 'COMPLETED' and not task.completed_date:
                    logger.warning(f"Task {task.id} has COMPLETED status but no completion date")
                elif task.status != 'COMPLETED' and task.completed_date:
                    logger.warning(f"Task {task.id} has completion date but status is {task.status}")
        except Exception as e:
            logger.warning(f"Error validating status consistency for task {task.id}: {str(e)}")

    def _process_task_content(self, task: Any) -> None:
        """Process task content like type and notes."""
        # Log task type
        if hasattr(task, 'type') and task.type:
            logger.debug(f"Task {task.id} is of type: {task.type}")

        # Process task notes
        if hasattr(task, 'notes') and task.notes:
            try:
                # Log note length for debugging
                note_length = len(task.notes) if task.notes else 0
                logger.debug(f"Task {task.id} has notes with {note_length} characters")

                # Could add content validation here (e.g., check for required fields)
            except Exception as e:
                logger.warning(f"Error processing notes for task {task.id}: {str(e)}")

    def _get_item_error_data(self, item: Any) -> Dict:
        """Get additional data for error logging specific to tasks."""
        return {'id': item.id, 'title': getattr(item, 'title', None), 'status': getattr(item, 'status', None), 'priority': getattr(item, 'priority', None), 'type': getattr(item, 'type', None),
                'due_date': getattr(item, 'due_date', None), 'completed_date': getattr(item, 'completed_date', None), 'contact_id': getattr(item, 'contact_id', None),
                'created_at': getattr(item, 'created_at', None), 'modified_at': getattr(item, 'modified_at', None)}
