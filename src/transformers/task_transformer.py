from datetime import datetime

from sqlalchemy.orm import Session
from src.utils.logger import get_logger

from src.models.models import Contact, Task

logger = get_logger(__name__)


class TaskTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Task:
        """Transform task data from Keap API to database model."""
        try:
            # Create or update task
            task = db.query(Task).filter_by(id=data['id']).first()
            if not task:
                task = Task(id=data['id'])

            # Update basic fields
            task.title = data.get('title')
            task.notes = data.get('notes')
            task.priority = data.get('priority')
            task.status = data.get('status')
            task.type = data.get('type')
            task.due_date = data.get('due_date')
            task.modified_at = datetime.utcnow()

            # Handle contact relationship
            if 'contact' in data:
                contact = db.query(Contact).filter_by(id=data['contact']['id']).first()
                if contact:
                    task.contact = contact

            # Merge the task itself
            db.merge(task)
            return task

        except Exception as e:
            logger.error(f"Error transforming task data: {str(e)}")
            raise
