import argparse
import traceback
import sys

from togglsync.version import VERSION
from togglsync.config import Config
from togglsync.toggl import TogglHelper
from togglsync.redmine import RedmineHelper
from togglsync.mattermost import MattermostNotifier, RequestsRunner
from togglsync import version


class Synchronizer:
    def __init__(self, config, redmine, toggl, mattermost):
        self.config = config
        self.redmine = redmine
        self.toggl = toggl
        self.mattermost = mattermost

        self.inserted = 0
        self.updated = 0
        self.skipped = 0

    def start(self, days):
        if days < 0:
            raise Exception("Invalid days: {}".format(days))

        entries = list(self.toggl.get(days))

        filteredEntries = TogglHelper.filterRedmineEntries(entries)

        print(
            "Found entries in toggl: {} (filtered: {})".format(
                len(entries), len(filteredEntries)
            )
        )

        if self.mattermost:
            self.mattermost.appendDuration(days)
            self.mattermost.appendEntries(entries)

        if len(filteredEntries) == 0:
            print("No entries with redmine id found. Nothing to do")
            return 0

        togglEntriesByIssueId = Synchronizer.groupTogglByIssueId(filteredEntries)

        for issueId in togglEntriesByIssueId:
            try:
                redmineEntries = list(self.redmine.get(issueId))
                filteredRedmineEntries = [
                    e for e in redmineEntries if e.toggl_id != None
                ]

                print(
                    "Found entries in redmine for issue {}: {} (with toggl id: {})".format(
                        issueId, len(redmineEntries), len(filteredRedmineEntries)
                    )
                )

                redmineEntriesByIssueId = Synchronizer.groupRedmineByIssueId(
                    filteredRedmineEntries
                )

                self.__sync(
                    issueId,
                    togglEntriesByIssueId[issueId],
                    redmineEntriesByIssueId[issueId]
                    if redmineEntriesByIssueId != None
                    and issueId in redmineEntriesByIssueId
                    else None,
                )
            except Exception as exc:
                traceback.print_exc()
                print()

        if self.mattermost:
            self.mattermost.append(
                "**{}** inserted, **{}** updated, **{}** skipped".format(
                    self.inserted, self.updated, self.skipped
                )
            )

    @staticmethod
    def groupTogglByIssueId(togglEntries):
        if togglEntries != None:
            groups = {}

            for e in togglEntries:
                if e.taskId == None:
                    continue

                if e.taskId not in groups:
                    groups[e.taskId] = []

                groups[e.taskId].append(e)

            return groups

    @staticmethod
    def groupRedmineByIssueId(redmineEntries):
        if redmineEntries != None:
            groups = {}

            for e in redmineEntries:
                if e.issue not in groups:
                    groups[e.issue] = []

                groups[e.issue].append(e)

            return groups

    def __sync(self, issueId, togglEntries, redmineEntries):
        print("Synchronizing {}".format(issueId))

        for togglEntry in togglEntries:
            redmineEntriesByTogglId = (
                [e for e in redmineEntries if e.toggl_id == togglEntry.id]
                if redmineEntries != None
                else []
            )

            if len(redmineEntriesByTogglId) == 0:
                # no entry in redmine found, should insert
                self.__insert_redmine_entry(togglEntry)
            elif len(redmineEntriesByTogglId) == 1:
                # if single found, try update
                self.__update_redmine_entry(togglEntry, redmineEntriesByTogglId[0])
            else:
                # if more found, remove all entries and insert new one
                self.__remove_redmine_entries(redmineEntriesByTogglId)
                self.__insert_redmine_entry(togglEntry)

        print()

    def __insert_redmine_entry(self, togglEntry):
        print("\tInserting into redmine: {}".format(togglEntry))
        data = togglEntry.toDict()
        self.redmine.put(**data)
        self.inserted += 1

    def __update_redmine_entry(self, togglEntry, redmineEntry):
        if self.__equal(togglEntry, redmineEntry):
            print("\tUp to date: {}".format(togglEntry))
            self.skipped += 1
        else:
            print("\tEntry changed, updating in redmine: {}".format(togglEntry))
            data = togglEntry.toDict()
            self.redmine.update(id=redmineEntry.id, **data)
            self.updated += 1

    def __remove_redmine_entries(self, redmineEntries):
        for e in redmineEntries:
            self.redmine.delete(e.id)
            print("\tRemoved in redmine: {}".format(e))

    @staticmethod
    def __equal(togglEntry, redmineEntry):
        togglEntryDict = togglEntry.toDict()

        if togglEntryDict["issueId"] != redmineEntry.issue:
            print(
                '\tentries not equal, issueId: "{}" vs "{}"'.format(
                    togglEntryDict["issueId"], redmineEntry.issue
                )
            )
            return False

        if togglEntryDict["spentOn"] != redmineEntry.spent_on:
            print(
                '\tentries not equal, spentOn: "{}" vs "{}"'.format(
                    togglEntryDict["spentOn"], redmineEntry.spent_on
                )
            )
            return False

        if togglEntryDict["hours"] != redmineEntry.hours:
            print(
                '\tentries not equal, hours: "{}" vs "{}"'.format(
                    togglEntryDict["hours"], redmineEntry.hours
                )
            )
            return False

        if togglEntryDict["comment"] != redmineEntry.comments:
            print(
                '\tentries not equal, comment: "{}" vs "{}"'.format(
                    togglEntryDict["comment"], redmineEntry.comments
                )
            )
            return False

        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Syncs toggle entries to redmine. Version v{}".format(VERSION)
    )

    parser.add_argument(
        "-s",
        "--simulation",
        help="No entries will be saved, only simulation",
        action="store_true",
    )
    parser.add_argument("-d", "--days", help="Days to sync", type=int, default=0)
    parser.add_argument("-v", "--version", help="Prints version", action="store_true")

    args = parser.parse_args()

    print("Synchronizer v{}\n============================".format(version.VERSION))

    if args.version:
        sys.exit(0)

    config = Config.fromFile()

    print("Found api key pairs: {}".format(len(config.entries)))

    mattermost = None

    if config.mattermost:
        runner = RequestsRunner.fromConfig(config.mattermost)
        mattermost = MattermostNotifier(runner, args.simulation)

    for apiKeys in config.entries:
        toggl = TogglHelper(config.toggl, apiKeys.toggl)
        redmine = RedmineHelper(config.redmine, apiKeys.redmine, args.simulation)

        if mattermost != None:
            mattermost.append(
                "TogglSync v{} for {}".format(version.VERSION, apiKeys.label)
            )
            mattermost.append("---")
            mattermost.append("")

        sync = Synchronizer(config, redmine, toggl, mattermost)
        sync.start(args.days)

    if mattermost != None:
        mattermost.send()
