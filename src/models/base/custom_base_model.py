from abc import ABC, abstractmethod

from pydantic import BaseModel
from pydantic_partial import PartialModelMixin


class CustomBaseModel(ABC, PartialModelMixin, BaseModel):
    @staticmethod
    @property
    @abstractmethod
    def BASE_URL(self) -> str:
        raise NotImplementedError

    @staticmethod
    @property
    @abstractmethod
    def ENDPOINT_PATH(self) -> str:
        raise NotImplementedError

    @property
    @staticmethod
    def PARTIAL(self):
        return super().model_as_partial()
