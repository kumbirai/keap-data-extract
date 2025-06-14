from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import Contact, Note
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NoteTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Note:
        """Transform note data from Keap API to database model."""
        try:
            # Create or update note
            note = db.query(Note).filter_by(id=data['id']).first()
            if not note:
                note = Note(id=data['id'])

            # Update basic fields
            note.title = data.get('title')
            note.body = data.get('body')
            note.created_at = data.get('created_at')
            note.last_updated = datetime.utcnow()

            # Handle contact relationship
            if 'contact' in data:
                contact = db.query(Contact).filter_by(id=data['contact']['id']).first()
                if contact:
                    # Clear existing contact relationships
                    note.contacts = []
                    note.contacts.append(contact)

            # Merge the note itself
            db.merge(note)
            return note

        except Exception as e:
            logger.error(f"Error transforming note data: {str(e)}")
            raise
