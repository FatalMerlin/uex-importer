from pydantic import BaseModel


class Wiki_Vehicle(BaseModel):
    uuid: str | None
    name: str
    link: str