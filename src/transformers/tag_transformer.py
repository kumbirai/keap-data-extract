from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from src.utils.logger import get_logger

from src.models.models import Tag

logger = get_logger(__name__)


class TagTransformer:
    @staticmethod
    def transform(data: Dict[str, Any], db: Session) -> Optional[Tag]:
        """Transform tag data from Keap API to database model.
        
        Args:
            data: Dictionary containing tag data from API
            db: Database session
            
        Returns:
            Tag model instance or None if transformation fails
        """
        try:
            if not isinstance(data, dict):
                logger.error(f"Invalid tag data format: {type(data)}")
                return None

            # Create or update tag
            tag = db.query(Tag).filter_by(id=data.get('id')).first()
        if not tag:
            tag = Tag(id=data.get('id'))
        db.add(tag)

        # Update basic fields
        tag.name = data.get('name')
        tag.description = data.get('description')
        tag.category = data.get('category')

        # Handle created_at timestamp
        created_at = data.get('created_at')
        if created_at:
            try:
                if isinstance(created_at, str):
                    tag.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                elif isinstance(created_at, (int, float)):
                    tag.created_at = datetime.fromtimestamp(created_at / 1000)  # Convert milliseconds to seconds
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing created_at for tag {tag.id}: {e}")
                tag.created_at = datetime.utcnow()
        else:

    tag.created_at = datetime.utcnow()

    return tag

    except Exception as e:
    logger.error(f"Error transforming tag data: {e}")
    return None
