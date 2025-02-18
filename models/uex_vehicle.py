# https://uexcorp.space/api/documentation/id/vehicles/
# https://api.uexcorp.space/2.0/vehicles
from pydantic import BaseModel


class UEX_Vehicle(BaseModel):
    id: int
    uuid: str | None
    name: str | None
    # all we care about for now