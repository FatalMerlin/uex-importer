from abc import ABC, abstractmethod
from typing import Type, ClassVar

from pydantic import BaseModel
from pydantic_partial import PartialModelMixin


class CustomBaseModel(ABC, PartialModelMixin, BaseModel):
    BASE_URL: ClassVar[str]
    ENDPOINT_PATH: ClassVar[str]

    @property
    @staticmethod
    def PARTIAL(self):
        return super().model_as_partial()

def CustomModel(base_url: str, endpoint_path: str):
    def wrapper(cls: Type['CustomBaseModel']):
        cls.BASE_URL = base_url
        cls.ENDPOINT_PATH = endpoint_path
        return cls

    return wrapper
