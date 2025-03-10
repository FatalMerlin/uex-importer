import numbers
from typing import Type, TypeVar, Callable, TypeAlias, Any

import structlog
from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn, TimeRemainingColumn, \
    MofNCompleteColumn
from structlog.stdlib import get_logger

from models.base.uex_base_model import UEXBaseModel
from models.base.wiki_base_model import WikiBaseModel
from models.uex.item import UEXItem
from models.uex.vehicle import UEXVehicle
from models.update import Update, UpdateStatus, UpdateList
from models.wiki.vehicle import WikiVehicle
from sync.uex import UEXSync
from sync.wiki import WikiSync
from updaters.uex import UEXUpdater
from utils.cache import write_cache, read_cache
from utils.validation import validate_value_path, get_attr_by_path


# def remove_exc_info(_, __, event_dict):
#     event_dict.pop("exc_info", None)  # Remove exc_info if present
#     return event_dict
#
#
# processors = [remove_exc_info]
#
# for processor in structlog.get_config()["processors"]:
#     if hasattr(processor, "__name__") and processor.__name__ == "set_exc_info":
#         continue
#     processors.append(processor)
#
# structlog.configure(
#     processors=processors,
# )

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,  # Captures exception details
        structlog.processors.ExceptionPrettyPrinter(),  # Pretty prints exceptions
        structlog.dev.ConsoleRenderer(),  # Human-readable console output
    ],
    context_class=dict,
    wrapper_class=structlog.make_filtering_bound_logger("DEBUG"),
    cache_logger_on_first_use=True,
)

TTarget = TypeVar('TTarget', bound=UEXBaseModel)
TSource = TypeVar('TSource', bound=WikiBaseModel)
UpdateMapping: TypeAlias = dict[str, str | tuple[str, Callable[[Any], Any]]]


class Main:
    def __init__(self, source_type: Type[TSource], target_type: Type[TTarget],
                 update_mapping: UpdateMapping, resource_type: UEXUpdater.ResourceType,
                 dry_run: bool = False):
        self.log = get_logger()
        self.source_type = source_type
        self.target_type = target_type
        self.target_type_partial = target_type.model_as_partial()
        self.mapping = update_mapping
        self.resource_type = resource_type
        self.dry_run = dry_run

        self.validate_mapping()

    def validate_mapping(self):
        self.log.info("Validating mapping...",
                      source_type=self.source_type.__name__,
                      target_type=self.target_type.__name__)

        for key, value in self.mapping.items():
            if not key in self.target_type.model_fields:
                raise ValueError(f"Invalid mapping key: '{key}' is not present in '{TTarget.__name__}'")

            if isinstance(value, tuple) and len(value) == 2 and isinstance(value[1], Callable):
                value = value[0]

            if value is None:
                # Default for shorthand fields
                # where key = value
                # meaning the fields have the same name and path
                value = key

            if not isinstance(value, str):
                raise ValueError(f"Invalid mapping value for key '{key}':"
                                 f" '{value}' is neither a Callable nor a string")

            validate_value_path(key, value, self.source_type)

        self.log.info("> Mapping validated")

    def get_cached_update_list(self) -> UpdateList[TTarget]:
        self.log.info("Loading cached update list...")
        update_list_raw = read_cache(f"{self.target_type.__name__}_updates")
        if update_list_raw is not None:
            self.log.info("> Cache loaded")
            update_list = UpdateList[TTarget].model_validate(update_list_raw)
        else:
            self.log.info("> Cache miss")
            update_list = UpdateList[TTarget]()

        return update_list

    def sync_wiki(self) -> (list[TSource], dict[str, TSource]):
        wiki_sync = WikiSync()
        wiki_entries = wiki_sync.sync(self.source_type)

        wiki_entry_dict = {
            wiki_entry.name: wiki_entry
            for wiki_entry in wiki_entries
        }

        return wiki_entries, wiki_entry_dict

    def sync_uex(self) -> (list[TTarget], dict[str, TTarget]):
        uex_sync = UEXSync()
        uex_entries = uex_sync.sync(self.target_type)

        uex_entry_dict = {
            uexItem.name: uexItem
            for uexItem in uex_entries
            if uexItem.name is not None
        }

        return uex_entries, uex_entry_dict

    def prepare_updates(self,
                        wiki_dict: dict[str, TSource],
                        uex_list: list[TTarget]
                        ) -> UpdateList[TTarget]:
        self.log.info("Preparing updates...")
        update_list = self.get_cached_update_list()

        count_no_source_match = 0
        count_updates_created = 0

        for uex_entry in uex_list:
            if uex_entry.id in update_list.updates and update_list.updates[uex_entry.id].status != UpdateStatus.PENDING:
                self.log.warn("Entity skipped, has processed update", name=uex_entry.name)
                continue

            if uex_entry.name not in wiki_dict:
                self.log.warn("Entity skipped, no matching wiki entry", name=uex_entry.name)
                count_no_source_match += 1
                continue

            wiki_entry = wiki_dict[uex_entry.name]
            changed_fields: list[str] = []
            update = Update(
                id=uex_entry.id,
                name=uex_entry.name,
                source_link=wiki_entry.link,
                status=UpdateStatus.PENDING,
                changes=self.target_type_partial()
            )

            for target_property, source_mapping in self.mapping.items():
                source_mapper = None
                if isinstance(source_mapping, tuple):
                    source_mapping, source_mapper = source_mapping

                if source_mapping is None:
                    source_mapping = target_property

                source_value = get_attr_by_path(wiki_entry, source_mapping)
                if source_value is None:
                    continue

                if source_mapper is not None:
                    try:
                        source_value = source_mapper(source_value)
                    except Exception as e:
                        self.log.warn("Error in mapping function", id=uex_entry.id, name=uex_entry.name,
                                      target_property=target_property, error=e,
                                      unexpected=True)
                        continue

                if isinstance(source_value, numbers.Number) and source_value == 0:
                    continue

                if getattr(uex_entry, target_property) == source_value:
                    continue

                setattr(update.changes, target_property, source_value)
                update.change_source_mapping[target_property] = source_mapping

                changed_fields.append(target_property)

            if len(changed_fields) == 0:
                self.log.warn("Entity skipped, no changes found", name=uex_entry.name)
                continue

            update_list.updates[uex_entry.id] = update
            count_updates_created += 1

            self.log.info("> Updated prepared", id=uex_entry.id, name=uex_entry.name,
                          changed_fields=changed_fields)

        write_cache(f"{self.target_type.__name__}_updates", update_list)
        self.log.info("Updates prepared", no_source_match=count_no_source_match,
                      updates_created=count_updates_created)

        return update_list

    def run(self):
        self.log.info("Starting UEX Database Updater...")
        wiki_list, wiki_dict = self.sync_wiki()
        uex_list, uex_dict = self.sync_uex()

        update_list = self.prepare_updates(wiki_dict, uex_list)
        self.log.info("")

        self.log.info("")
        self.log.info("Beginning UEX Database Update")
        self.log.info("")

        self.update(self.resource_type, update_list)

        self.log.info("")
        self.log.info("Finished UEX Database Updated")
        self.log.info("")

        self.log.info("Finished UEX DatabaseUpdater")

    def update(self, resource_type: UEXUpdater.ResourceType, update_list: UpdateList[TTarget]):
        sorted_updates = sorted(update_list.updates.values(), key=lambda u: u.id)

        with UEXUpdater() as uexUpdater, Progress() as progress:
            progress.columns = [
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn()
            ]

            task = progress.add_task(f"Updating {resource_type.value}", total=len(sorted_updates))

            for update in sorted_updates:  # track(sorted_updates, description=f"Updating {resource_type.value}", ):
                progress.update(task, advance=1)

                try:
                    if uexUpdater.update(resource_type, update, dry_run=self.dry_run):
                        update.status = UpdateStatus.SUBMITTED
                    else:
                        update.status = UpdateStatus.FAILED
                except Exception as e:
                    self.log.error("Failed to update", id=update.id, name=update.name, error=e, unexpected=True)
                    update.status = UpdateStatus.FAILED

                update_list.updates[update.id] = update
                if self.dry_run:
                    continue

                write_cache(f"{self.target_type.__name__}_updates", update_list)


if __name__ == '__main__':
    # mapper function that returns the source property from the source entity for the given target_key
    mapping: UpdateMapping = {
        # target_key: source_property
        # target_key = source_property
        # Vehicle UUIDs were fixed!
        **dict.fromkeys([
            'uuid',
        ]),
        # individual mappings
        'scu': 'cargo_capacity',
        'crew': ('crew', lambda crew: ','.join(
            [
                str(m) for m in [crew.min, crew.max]
                if m is not None
            ]),
        ),
        'mass': 'mass',
        'width': 'sizes.beam',
        'height': 'sizes.height',
        'length': 'sizes.length',
        'fuel_quantum': 'quantum.quantum_fuel_capacity',
        'fuel_hydrogen': 'fuel.capacity',
    }

    Main(WikiVehicle, UEXVehicle, mapping, UEXUpdater.ResourceType.VEHICLE, False).run()
