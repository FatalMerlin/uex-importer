from enum import StrEnum
from typing import TypeVar, Generic

from pydantic import BaseModel, Field

from models.base.uex_base_model import UEXBaseModel

T = TypeVar('T', bound=UEXBaseModel)

class UpdateStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FAILED = "failed"

class Update(BaseModel, Generic[T]):
    id: int
    name: str
    status: UpdateStatus
    changes: T

class UpdateList(BaseModel, Generic[T]):
    updates: dict[int, Update[T]] = Field(default_factory=dict)