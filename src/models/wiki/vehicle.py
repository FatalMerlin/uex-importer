from pydantic import BaseModel

from models.base.wiki_base_model import WikiBaseModel, WikiModel, WikiPaginatedModel


class WikiVehiclePaginated(WikiPaginatedModel):
    uuid: str | None
    name: str | None


class WikiVehicleSizes(BaseModel):
    length: float | None
    beam: float | None
    height: float | None


class WikiVehicleCrew(BaseModel):
    min: int | None
    max: int | None


class WikiVehicleFuel(BaseModel):
    capacity: int | None


class WikiVehicleQuantum(BaseModel):
    quantum_speed: int | None
    quantum_spool_time: int | None
    quantum_fuel_capacity: int | None
    quantum_range: int | None


@WikiModel('/v3/vehicles', True, WikiVehiclePaginated)
class WikiVehicle(WikiBaseModel):
    uuid: str | None
    name: str | None
    slug: str | None
    link: str
    class_name: str | None
    sizes: WikiVehicleSizes | None
    mass: int | None
    cargo_capacity: float | None
    crew: WikiVehicleCrew | None
    fuel: WikiVehicleFuel | None
    quantum: WikiVehicleQuantum | None

