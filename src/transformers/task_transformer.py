from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import Task, Contact


class TaskTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Task:
        """Transform task data from Keap API to database model."""
        # Create or update task
        task = db.query(Task).filter_by(id=data['id']).first()
        if not task:
            task = Task(id=data['id'])
            db.add(task)

        # Update basic fields
        task.title = data.get('title')
        task.description = data.get('description')
        task.due_date = data.get('due_date')
        task.status = data.get('status')
        task.last_updated = datetime.utcnow()

        # Handle contact relationship
        if 'contact' in data:
            contact = db.query(Contact).filter_by(id=data['contact']['id']).first()
            if contact:
                # Clear existing contact relationships
                task.contacts = []
                task.contacts.append(contact)

        return task
