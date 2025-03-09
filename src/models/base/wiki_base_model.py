from abc import ABC
from functools import wraps
from typing import ClassVar, Optional, Type, Callable

from models.base.custom_base_model import CustomBaseModel


class WikiBaseModel(CustomBaseModel, ABC):
    BASE_URL: ClassVar[str] = 'https://api.star-citizen.wiki/api'
    IS_PAGINATED: ClassVar[bool] = False
    PAGINATION_MODEL: ClassVar[Optional[Type['WikiPaginatedModel']]] = None


def WikiModel(
        endpoint_path: str,
        is_paginated: bool = False,
        pagination_model: Optional[Type['WikiBaseModel']] = None
) -> Callable[[Type[WikiBaseModel]], Type[WikiBaseModel]]:
    def wrapper(cls: Type['WikiBaseModel']) -> Type['WikiBaseModel']:
        cls.BASE_URL = 'https://api.star-citizen.wiki/api'
        cls.ENDPOINT_PATH = endpoint_path
        cls.IS_PAGINATED = is_paginated
        cls.PAGINATION_MODEL = pagination_model
        return cls
    return wrapper

class WikiPaginatedModel(WikiBaseModel):
    link: str
    updated_at: str
    version: str | None