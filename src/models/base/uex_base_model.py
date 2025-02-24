from abc import ABC, abstractmethod
from typing import ClassVar, Callable, Optional, Type

from models.base.custom_base_model import CustomBaseModel


class UEXBaseModel(CustomBaseModel, ABC):
    BASE_URL: ClassVar[str] = 'https://api.uexcorp.space/2.0'

    FOREACH: ClassVar[Optional[Type['UEXBaseModel']]] = None
    FOREACH_MAP: ClassVar[Optional[Callable[['UEXBaseModel'], str]]] = None
