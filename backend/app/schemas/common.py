from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated wrapper for list endpoints."""

    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool


class MessageResponse(BaseModel):
    """Simple message response for success/error operations."""

    message: str
    success: bool = True
