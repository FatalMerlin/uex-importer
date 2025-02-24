from datetime import datetime
from typing import ClassVar

from models.base.uex_base_model import UEXBaseModel


class UEXCategory(UEXBaseModel):
    ENDPOINT_PATH: ClassVar[str] = '/categories'

    id: int  # (11)
    type: str | None  # (255) // item, service
    section: str | None  # (255) // category group
    name: str | None  # (255) // category name
    is_game_related: bool  # (1) // if the category exists in-game
    is_mining: bool  # (1) // if it's mining related category
    date_added: datetime  # (11) // timestamp
    date_modified: datetime  # (11) // timestamp
