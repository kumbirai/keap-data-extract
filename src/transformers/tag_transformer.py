from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import Tag


class TagTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Tag:
        """Transform tag data from Keap API to database model."""
        # Create or update tag
        tag = db.query(Tag).filter_by(id=data['id']).first()
        if not tag:
            tag = Tag(id=data['id'])
            db.add(tag)

        # Update basic fields
        tag.name = data.get('name')
        tag.description = data.get('description')
        tag.category = data.get('category')
        tag.created_at = datetime.utcnow()

        return tag
