from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.models.models import Contact, Tag, TagCategory
from src.utils.logger import get_logger

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

            # Create tag instance
            tag = Tag(**data)

            # Handle relationships
            if 'contacts' in data:
                for contact_data in data['contacts']:
                    contact = db.query(Contact).filter_by(id=contact_data['id']).first()
                    if contact:
                        tag.contacts.append(contact)

            # Handle category relationship
            if 'category' in data:
                category = db.query(TagCategory).filter_by(id=data['category']['id']).first()
                if category:
                    tag.category = category

            # Merge the tag itself
            db.merge(tag)
            return tag

        except Exception as e:
            logger.error(f"Error transforming tag data: {str(e)}")
            return None
