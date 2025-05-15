from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class Preferences(BaseModel):
    """User food preferences and restrictions"""

    likes: list[str] = Field(description="Foods the user likes", default_factory=list)
    dislikes: list[str] = Field(
        description="Foods the user doesn't like", default_factory=list
    )
    dietary_restrictions: list[str] = Field(
        description="Any dietary restrictions", default_factory=list
    )
    cooking_goals: list[str] = Field(
        description="Food or cooking related goals", default_factory=list
    )


class Ingredients(BaseModel):
    """User ingredients"""

    names: list[str] = Field(
        description="Ingredients the user have", default_factory=list
    )


class UpdateMemory(TypedDict):
    """Decision on what memory type to update"""

    update_type: Literal["preferences", "ingredients"]
