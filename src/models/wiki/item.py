from typing import ClassVar

from models.base.wiki_base_model import WikiBaseModel

### reference
# {
#     "uuid": "4a4a2a9c-040f-4f36-befe-7101b230fa53",
#     "name": "PowerBolt",
#     "type": "PowerPlant",
#     "sub_type": "Power",
#     "is_base_variant": true,
#     "manufacturer": {
#         "name": "Lightning Power Ltd.",
#         "code": "LPLT",
#         "link": "https:\/\/api.star-citizen.wiki\/api\/v2\/manufacturers\/Lightning+Power+Ltd."
#     },
#     "link": "https:\/\/api.star-citizen.wiki\/api\/v2\/items\/4a4a2a9c-040f-4f36-befe-7101b230fa53",
#     "updated_at": "2025-02-21T04:41:17.000000Z",
#     "version": "4.0.1-LIVE.9499080"
# },


class WikiItem(WikiBaseModel):
    ENDPOINT_PATH: ClassVar[str] = '/v2/items'
    IS_PAGINATED: ClassVar[bool] = True

    uuid: str
    name: str
    type: str
    sub_type: str
    is_base_variant: bool
    manufacturer: dict
    link: str
    updated_at: str
    version: str
