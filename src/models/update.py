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
    source_link: str
    status: UpdateStatus
    # uex property name -> wiki property name
    change_source_mapping: dict[str, str] = Field(default_factory=dict)
    changes: T

class UpdateList(BaseModel, Generic[T]):
    updates: dict[int, Update[T]] = Field(default_factory=dict)