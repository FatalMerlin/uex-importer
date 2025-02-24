from datetime import datetime
from typing import ClassVar, Callable

from models.base.uex_base_model import UEXBaseModel
from models.uex.category import UEXCategory


class UEXItem(UEXBaseModel):
    ENDPOINT_PATH: ClassVar[str] = '/items'
    FOREACH: ClassVar[UEXBaseModel] = UEXCategory
    FOREACH_MAP: ClassVar[Callable[[UEXCategory], str]] = lambda category: f"?id_category={category.id}"

    id: int  # (11) // route ID, may change during website updates
    id_parent: int  # (11)
    id_category: int  # (11)
    id_company: int  # (11)
    id_vehicle: int  # (11) // if linked to a vehicle
    name: str | None  # (255)
    section: str | None  # (255) // coming from categories
    category: str | None  # (255) // coming from categories
    company_name: str | None  # (255) // coming from companies
    vehicle_name: str | None  # (255) // coming from vehicles
    slug: str | None  # (255) // UEX URLs
    uuid: str | None  # (255) // star citizen uuid
    url_store: str | None  # (255) // pledge store URL
    is_exclusive_pledge: bool  # (1)
    is_exclusive_subscriber: bool  # (1)
    is_exclusive_concierge: bool  # (1)
    # screenshot:  str | None # (255) // item image URL (suspended due to server costs)
    # attributes:  json // deprecated, replaced by items_attributes
    notification: str | None  # json // heads up about an item, such as known bugs, etc.
    date_added: datetime  # (11) // timestamp
    date_modified: datetime  # (11) // timestamp
