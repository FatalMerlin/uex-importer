import json
import os

from main import read_cache
from old.uex_vehicle import UEX_Vehicle

file_dir = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(file_dir, 'cache')
update_json_file = os.path.join(cache_dir, 'uex_vehicles_updated.json')
submitted_json_file = os.path.join(cache_dir, 'uex_vehicles_submitted.json')

updated = [UEX_Vehicle(**vehicle) for vehicle in json.loads(read_cache('uex_vehicles_updated.json'))]
submitted = json.loads(read_cache('uex_vehicles_submitted.json'))

missing_from_submitted = [vehicle for vehicle in updated if str(vehicle.id) not in submitted]

print(len(missing_from_submitted))

for vehicle in missing_from_submitted:
    print(
        "https://uexcorp.space/data/submit/type/request?resource=vehicles&request_action=edit&id_reference={id}".format(
            id=vehicle.id),
        vehicle.name,
        vehicle.uuid
    )
