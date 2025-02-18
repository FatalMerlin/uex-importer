import json
import logging
import os

import requests
from dotenv import load_dotenv

from models.uex_vehicle import UEX_Vehicle
from models.wiki_vehicle import Wiki_Vehicle

file_dir = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(file_dir, 'cache')

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s')
log = logging.getLogger(__name__)


def main():
    load_dotenv()

    vehicles = load_uex_vehicles()

    vehicles_with_uuid = [vehicle for vehicle in vehicles if vehicle.uuid]
    vehicles_without_uuid = [vehicle for vehicle in vehicles if not vehicle.uuid]

    log.info(
        f'Loaded {len(vehicles)} vehicles,'
        f' with UUID: {len(vehicles_with_uuid)} ({(len(vehicles_with_uuid) / len(vehicles) * 100):.2f}%),'
        f' without UUID: {len(vehicles_without_uuid)} ({(len(vehicles_without_uuid) / len(vehicles) * 100):.2f}%) total')

    wiki_vehicles = load_wiki_vehicles()
    wiki_vehicles_with_uuid = [vehicle for vehicle in wiki_vehicles if vehicle.uuid]
    wiki_vehicles_without_uuid = [vehicle for vehicle in wiki_vehicles if not vehicle.uuid]
    log.info(f'Loaded {len(wiki_vehicles)} wiki vehicles,'
             f' with UUID: {len(wiki_vehicles_with_uuid)} ({(len(wiki_vehicles_with_uuid) / len(wiki_vehicles) * 100):.2f}%),'
             f' without UUID: {len(wiki_vehicles_without_uuid)} ({(len(wiki_vehicles_without_uuid) / len(wiki_vehicles) * 100):.2f}%) total')

    name_uuid_dict = {vehicle.name: vehicle.uuid for vehicle in wiki_vehicles_with_uuid}

    updated_vehicles: list[UEX_Vehicle] = []

    for vehicle in vehicles_without_uuid:
        name = vehicle.name
        uuid = name_uuid_dict.get(name)
        if uuid:
            vehicle.uuid = uuid
            updated_vehicles.append(vehicle)
            log.info(f'Updated vehicle {name} with UUID {uuid}')

    result = json.dumps([vehicle.__dict__ for vehicle in updated_vehicles], indent=4)
    write_cache('uex_vehicles_updated.json', result)


def load_uex_vehicles() -> list[UEX_Vehicle]:
    response = fetch_or_cache('https://api.uexcorp.space/2.0/vehicles', 'uex_vehicles.json')
    response_json = json.loads(response)
    response_data = response_json['data']

    vehicles = [UEX_Vehicle(**vehicle) for vehicle in response_data]

    return vehicles


def load_wiki_vehicles() -> list[Wiki_Vehicle]:
    next_page = "https://api.star-citizen.wiki/api/v3/vehicles?limit=50&locale=en_EN"
    page_index = 0

    vehicles: list[Wiki_Vehicle] = []

    while next_page:
        page_index += 1

        response = fetch_or_cache(next_page, f'wiki_vehicles_{page_index}.json')
        parsed = json.loads(response)

        links = parsed['links']
        next_page = links['next']
        data = parsed['data']

        for vehicle in data:
            vehicles.append(Wiki_Vehicle(**vehicle))

    return vehicles


def fetch_or_cache(url: str, file_name: str | None = None):
    cache_file_name = file_name or url.split('/')[-1] or url.split('/')[-2]

    if not cache_file_name.endswith('.json'):
        cache_file_name += '.json'

    contents = read_cache(cache_file_name)

    if not contents:
        log.info("Cache MISS: %s" % url)
        response = requests.get(url)
        contents = response.text
        write_cache(cache_file_name, contents)
    else:
        log.info("Cache HIT: %s" % url)

    return contents


def write_cache(file: str, contents: str):
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    file = os.path.join(cache_dir, file)

    with open(file, 'w') as f:
        f.write(contents)
        f.flush()
        f.close()


def read_cache(file: str) -> str | None:
    file = os.path.join(cache_dir, file)

    if not os.path.exists(file):
        return None

    with open(file, 'r') as f:
        contents = f.read()
        f.close()
        return contents


if __name__ == '__main__':
    main()
