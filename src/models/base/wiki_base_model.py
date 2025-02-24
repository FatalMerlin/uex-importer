from abc import ABC
from typing import ClassVar

from models.base.custom_base_model import CustomBaseModel


class WikiBaseModel(CustomBaseModel, ABC):
    BASE_URL: ClassVar[str] = 'https://api.star-citizen.wiki/api'
    IS_PAGINATED: ClassVar[bool] = False