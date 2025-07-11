"""
Base models and configuration for The Assistant.

This module provides the foundation for all data models using Pydantic v2
with proper JSON serialization support for Temporal workflows.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseAssistantModel(BaseModel):
    """
    Base model for all Assistant data structures.

    Provides consistent configuration and JSON serialization
    that works with Temporal's payload conversion.
    """

    model_config = ConfigDict(
        # Enable validation on assignment
        validate_assignment=True,
        # Use enum values instead of names in serialization
        use_enum_values=True,
        # Allow extra fields for flexibility with external APIs
        extra="ignore",  # Changed from "forbid" to "ignore" to handle computed fields
        # Validate default values
        validate_default=True,
        # Custom JSON encoders for datetime objects
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        },
        # Enable arbitrary types for Path objects
        arbitrary_types_allowed=True,
    )

    def model_dump_temporal(self) -> dict[str, Any]:
        """
        Serialize model for Temporal payload conversion.

        Returns a dictionary that can be safely serialized to JSON
        and passed between Temporal activities and workflows.
        """
        return self.model_dump(
            mode="json",
            exclude_none=True,
            by_alias=True,
        )

    @classmethod
    def model_validate_temporal(cls, data: dict[str, Any]) -> "BaseAssistantModel":
        """
        Deserialize model from Temporal payload.

        Args:
            data: Dictionary from Temporal payload conversion

        Returns:
            Validated model instance
        """
        return cls.model_validate(data)
