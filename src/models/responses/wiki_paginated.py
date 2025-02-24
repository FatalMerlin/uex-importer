from typing import TypeVar, Generic

from pydantic import BaseModel, Field

T = TypeVar("T")

class Links(BaseModel):
    first: str
    last: str
    prev: str | None
    next: str | None

class Meta(BaseModel):
    current_page: int
    from_: int = Field(alias="from")
    last_page: int
    path: str
    per_page: int
    to: int
    total: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    links: Links
    meta: Meta

