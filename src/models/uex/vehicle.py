from typing import ClassVar

from models.base.uex_base_model import UEXBaseModel


class UEXVehicle(UEXBaseModel):
    ENDPOINT_PATH: ClassVar[str] = '/vehicles'

    id: int
    uuid: str | None
    name: str | None
    name_full: str | None
    slug: str | None

    scu: float
    crew: str | None
    mass: float | None
    width: float | None
    height: float | None
    length: float | None
    fuel_quantum: float | None
    fuel_hydrogen: float | None
