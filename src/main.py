import colorama
import structlog
from rich.progress import Progress, track, BarColumn, TextColumn, TaskProgressColumn, TimeRemainingColumn, \
    MofNCompleteColumn
from structlog.stdlib import get_logger

from models.uex.item import UEXItem
from models.update import Update, UpdateStatus, UpdateList
from models.wiki.item import WikiItem
from sync.uex import UEXSync
from sync.wiki import WikiSync
from updaters.uex import UEXUpdater
from utils.cache import write_cache, read_cache


def remove_exc_info(_, __, event_dict):
    event_dict.pop("exc_info", None)  # Remove exc_info if present
    return event_dict


processors = [remove_exc_info]

for processor in structlog.get_config()["processors"]:
    if hasattr(processor, "__name__") and processor.__name__ == "set_exc_info":
        continue
    processors.append(processor)

structlog.configure(
    processors=processors,
)

PartialItem = UEXItem.model_as_partial()


class Main:
    def __init__(self):
        self.log = get_logger()

    def run(self):
        self.log.info("Starting UEX UUID Updater...")

        update_list_raw = read_cache(f"{UEXItem.__name__}_updates")
        if update_list_raw is not None:
            update_list = UpdateList[PartialItem].model_validate(update_list_raw)
        else:
            update_list = UpdateList[PartialItem]()

        wikiSync = WikiSync()
        wikiItems = wikiSync.sync(WikiItem)

        uexSync = UEXSync()
        uexItems = uexSync.sync(UEXItem)

        wikiItemDict = {
            wikiItem.name: wikiItem
            for wikiItem in wikiItems
            if wikiItem.uuid is not None
               and wikiItem.uuid != ""
        }

        uexItemDict = {
            uexItem.name: uexItem
            for uexItem in uexItems
            if uexItem.name is not None
        }

        has_uuid = 0
        empty_uuid = 0
        pending_update = 0

        for uexItem in uexItems:
            if uexItem.id in update_list.updates:
                pending_update += 1
                self.log.warn("Item skipped, has pending update", name=uexItem.name)
                continue

            if uexItem.uuid is not None:
                if uexItem.uuid.strip() != "":
                    self.log.warn("Item skipped, already has UUID", name=uexItem.name, uuid=uexItem.uuid)
                    has_uuid += 1
                    continue
                self.log.warn("Item has empty UUID", name=uexItem.name, uuid=uexItem.uuid,
                              uuid_str_len=len(uexItem.uuid))
                empty_uuid += 1

            if uexItem.name in wikiItemDict:
                wikiItem = wikiItemDict[uexItem.name]

                changes = PartialItem(uuid=wikiItem.uuid)

                update = Update(
                    id=uexItem.id,
                    name=uexItem.name,
                    status=UpdateStatus.PENDING,
                    changes=changes
                )

                update_list.updates[uexItem.id] = update

                self.log.info("Found UUID Match", name=uexItem.name, uuid=update.changes.uuid)

        write_cache(f"{UEXItem.__name__}_updates", update_list)

        self.log.info("")
        self.log.info(f"Finished UUID Matching", model=UEXItem.__name__, matched=len(update_list.updates),
                      has_uuid=has_uuid,
                      empty_uuid=empty_uuid, not_found=len(uexItems) - len(update_list.updates),
                      pending_update=pending_update)
        self.log.info("")

        self.log.info("")
        self.log.info("Beginning UEX Update")
        self.log.info("")

        self.update(UEXUpdater.ResourceType.ITEM, update_list)

        self.log.info("")
        self.log.info("Finished UEX Updated")
        self.log.info("")

        self.log.info("Finished UEX UUID Updater")

    def update(self, resource_type: UEXUpdater.ResourceType, update_list: UpdateList[PartialItem]):
        sorted_updates = sorted(update_list.updates.values(), key=lambda update: update.id)

        with UEXUpdater() as uexUpdater, Progress() as progress:
            progress.columns = [
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn()
            ]

            task = progress.add_task(f"Updating {resource_type.value}", total=len(sorted_updates))

            for update in sorted_updates:  #track(sorted_updates, description=f"Updating {resource_type.value}", ):
                progress.update(task, advance=1)

                try:
                    if uexUpdater.update(resource_type, update):
                        update.status = UpdateStatus.SUBMITTED
                    else:
                        update.status = UpdateStatus.FAILED
                except Exception as e:
                    self.log.error("Failed to update", id=update.id, name=update.name, error=e, unexpected=True)
                    update.status = UpdateStatus.FAILED

                update_list.updates[update.id] = update

                write_cache(f"{UEXItem.__name__}_updates", update_list)


if __name__ == '__main__':
    Main().run()
