"""
Factory class for creating entity loaders.

This module provides a factory pattern to create the appropriate loader
for each entity type, eliminating the massive if/elif chains in the main function.
"""

from typing import Any, Dict, Type

from sqlalchemy.orm import Session

from src.api.keap_client import KeapClient
from .affiliate_loader import AffiliateLoader
from .base_loader import BaseEntityLoader, EntityLoader
from .campaign_loader import CampaignLoader
from .contact_loader import ContactLoader
from .custom_fields_loader import CustomFieldsLoader
from .note_loader import NoteLoader
from .opportunity_loader import OpportunityLoader
from .order_loader import OrderLoader
from .product_loader import ProductLoader
from .subscription_loader import SubscriptionLoader
from .tags_loader import TagsLoader
from .task_loader import TaskLoader


class LoaderFactory:
    """Factory class to create appropriate loaders for different entity types.
    
    This factory eliminates the massive if/elif chains that were in the
    original main function by providing a clean mapping of entity types
    to their corresponding loaders.
    """

    # Registry of loaders for different entity types
    _loaders: Dict[str, Type[EntityLoader]] = {}

    @classmethod
    def register_loader(cls, entity_type: str, loader_class: Type[EntityLoader]) -> None:
        """Register a loader class for an entity type."""
        cls._loaders[entity_type] = loader_class

    @classmethod
    def create_loader(cls, entity_type: str, client: KeapClient, db: Session, checkpoint_manager: Any) -> EntityLoader:
        """Create a loader for the specified entity type.
        
        Args:
            entity_type: The type of entity to load
            client: KeapClient instance
            db: Database session
            checkpoint_manager: Checkpoint manager instance
            
        Returns:
            An appropriate EntityLoader instance
            
        Raises:
            ValueError: If no loader is registered for the entity type
        """
        # Check if we have a specialized loader
        if entity_type in cls._loaders:
            loader_class = cls._loaders[entity_type]
            return loader_class(client, db, checkpoint_manager)

        # For simple entities, use the base loader with method mapping
        method_mapping = cls._get_method_mapping()
        if entity_type in method_mapping:
            get_method, get_by_id_method = method_mapping[entity_type]
            return BaseEntityLoader(client, db, checkpoint_manager, entity_type, get_method, get_by_id_method)

        raise ValueError(f"Unknown entity type: {entity_type}")

    @classmethod
    def _get_method_mapping(cls) -> Dict[str, tuple]:
        """Get mapping of entity types to their API methods."""
        return {  # Note: subscriptions removed from here since they don't follow the standard pattern
        }

    @classmethod
    def get_supported_entity_types(cls) -> list:
        """Get list of all supported entity types."""
        specialized_types = list(cls._loaders.keys())
        method_types = list(cls._get_method_mapping().keys())
        return list(set(specialized_types + method_types))


# Register specialized loaders
LoaderFactory.register_loader('contacts', ContactLoader)
LoaderFactory.register_loader('custom_fields', CustomFieldsLoader)
LoaderFactory.register_loader('tags', TagsLoader)
LoaderFactory.register_loader('opportunities', OpportunityLoader)
LoaderFactory.register_loader('orders', OrderLoader)
LoaderFactory.register_loader('products', ProductLoader)
LoaderFactory.register_loader('affiliates', AffiliateLoader)
LoaderFactory.register_loader('subscriptions', SubscriptionLoader)
LoaderFactory.register_loader('tasks', TaskLoader)
LoaderFactory.register_loader('notes', NoteLoader)
LoaderFactory.register_loader('campaigns', CampaignLoader)

# Note: Additional specialized loaders would be registered here:
# LoaderFactory.register_loader('orders', OrderLoader)
# LoaderFactory.register_loader('products', ProductLoader)
# LoaderFactory.register_loader('affiliates', AffiliateLoader)
