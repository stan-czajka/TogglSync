import argparse
import os
import sys
import traceback
from getpass import getpass

import dateutil.parser
from termcolor import colored

from togglsync import version
from togglsync.config import Config, Entry, Colors
from togglsync.jira_wrapper import JiraHelper
from togglsync.mattermost import MattermostNotifier, RequestsRunner
from togglsync.redmine_wrapper import RedmineHelper
from togglsync.toggl import TogglHelper
from togglsync.version import VERSION


class Synchronizer:
    def __init__(self, config, api_helper, toggl, mattermost, raise_errors=False):
        self.config = config
        self.api_helper = api_helper
        self.toggl = toggl
        self.mattermost = mattermost

        self.inserted = 0
        self.updated = 0
        self.skipped = 0
        self.raise_errors = raise_errors

    def start(self, days):
        if days < 0:
            raise Exception("Invalid days: {}".format(days))

        entries = list(self.toggl.get(days))

        filteredEntries = self.toggl.filter_valid_entries(entries)

        print(
            "Found entries in toggl: {} (filtered: {})".format(
                len(entries), len(filteredEntries)
            )
        )

        if self.mattermost:
            self.mattermost.appendDuration(days)
            self.mattermost.appendEntries(entries)

        if len(filteredEntries) == 0:
            print("No entries with tracking id found. Nothing to do")
            return 0

        togglEntriesByIssueId = Synchronizer.groupTogglByIssueId(filteredEntries)

        for issueId in togglEntriesByIssueId:
            try:
                destination_entries = list(self.api_helper.get(issueId))
                filtered_destination_entries = [
                    e for e in destination_entries if e.toggl_id is not None
                ]

                print(
                    "Found entries in destination for issue {}: {} (with toggl id: {})".format(
                        issueId,
                        len(destination_entries),
                        len(filtered_destination_entries),
                    )
                )

                dest_entries_by_issue_id = Synchronizer.groupDestinationByIssueId(
                    filtered_destination_entries
                )

                self.__sync(
                    issueId,
                    togglEntriesByIssueId[issueId],
                    dest_entries_by_issue_id[issueId]
                    if dest_entries_by_issue_id is not None
                    and issueId in dest_entries_by_issue_id
                    else None,
                )
            except Exception as exc:
                traceback.print_exc()
                print()
                if self.raise_errors:
                    raise

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
    def groupDestinationByIssueId(destinationEntries):
        if destinationEntries != None:
            groups = {}

            for e in destinationEntries:
                if e.issue not in groups:
                    groups[e.issue] = []

                groups[e.issue].append(e)

            return groups

    def __sync(self, issueId, togglEntries, existingDestinationEntries):
        print("Synchronizing {}".format(issueId))

        for togglEntry in togglEntries:
            dest_entries_by_toggl_id = (
                [e for e in existingDestinationEntries if e.toggl_id == togglEntry.id]
                if existingDestinationEntries is not None
                else []
            )

            if len(dest_entries_by_toggl_id) == 0:
                # no entry in destination found, should insert
                self.__insert_entry_in_destination(togglEntry)
            elif len(dest_entries_by_toggl_id) == 1:
                # if single found, try update
                self.__update_entry_in_destination(
                    togglEntry, dest_entries_by_toggl_id[0]
                )
            else:
                # if more found, remove all entries and insert new one
                self.__remove_entries_in_destination(dest_entries_by_toggl_id)
                self.__insert_entry_in_destination(togglEntry)

        print()

    def __insert_entry_in_destination(self, togglEntry):
        print(colored("\tInserting into destination: {}".format(togglEntry), Colors.ADD.value))
        data = self.api_helper.dictFromTogglEntry(togglEntry)
        self.api_helper.put(**data)
        self.inserted += 1

    def __update_entry_in_destination(self, togglEntry, existing_destination_entry):
        if self._equal(togglEntry, existing_destination_entry):
            print("\tUp to date: {}".format(togglEntry))
            self.skipped += 1
        else:
            print(colored("\tEntry changed, updating in destination: {}".format(togglEntry), Colors.UPDATE.value))
            data = self.api_helper.dictFromTogglEntry(togglEntry)
            self.api_helper.update(id=existing_destination_entry.id, **data)
            self.updated += 1

    def __remove_entries_in_destination(self, destination_entries):
        for e in destination_entries:
            self.api_helper.delete(e.id)
            print(colored("\tRemoved in destination: {}".format(e), Colors.UPDATE.value))

    def _equal(self, toggl_entry, destination_entry):
        togglEntryDict = self.api_helper.dictFromTogglEntry(toggl_entry)

        if togglEntryDict["issueId"] != destination_entry.issue:
            print(
                '\tentries not equal, issueId: "{}" vs "{}"'.format(
                    togglEntryDict["issueId"], destination_entry.issue
                )
            )
            return False

        # when comapring by seconds, accuracy has to be rounded to minutes
        # Jira API rounds/truncates to minutes event though data is provided in seconds
        if "seconds" in togglEntryDict and not self._eq_to_minutes(
            togglEntryDict["seconds"], destination_entry.seconds
        ):
            print(
                '\tentries not equal, seconds (accuracy to minutes): "{}" vs "{}"'.format(
                    togglEntryDict["seconds"], destination_entry.seconds
                )
            )
            return False

        if "started" in togglEntryDict and not self._eq_datetime_str(
            togglEntryDict["started"], destination_entry.spent_on
        ):
            print(
                '\tentries not equal, started: "{}" vs "{}"'.format(
                    togglEntryDict["started"], destination_entry.spent_on
                )
            )
            return False

        if (
            "spentOn" in togglEntryDict
            and togglEntryDict["spentOn"] != destination_entry.spent_on
        ):
            print(
                '\tentries not equal, spentOn: "{}" vs "{}"'.format(
                    togglEntryDict["spentOn"], destination_entry.spent_on
                )
            )
            return False

        if (
            "hours" in togglEntryDict
            and togglEntryDict["hours"] != destination_entry.hours
        ):
            print(
                '\tentries not equal, hours: "{}" vs "{}"'.format(
                    togglEntryDict["hours"], destination_entry.hours
                )
            )
            return False

        if togglEntryDict["comment"] != destination_entry.comments:
            print(
                '\tentries not equal, comment: "{}" vs "{}"'.format(
                    togglEntryDict["comment"], destination_entry.comments
                )
            )
            return False

        return True

    @staticmethod
    def _eq_to_minutes(source_seconds, target_seconds):
        return abs(source_seconds - target_seconds) < 60

    @staticmethod
    def _eq_datetime_str(source_time: str, target_time: str):
        # comparing wo/ microseconds
        source = dateutil.parser.parse(source_time).replace(microsecond=0)
        target = dateutil.parser.parse(target_time).replace(microsecond=0)
        return source == target


class ApiHelperFactory:
    pass_cache = {}

    def __init__(self, config_entry: Entry):
        self.config_entry = config_entry

    @property
    def jira_pass(self):
        if self.config_entry.jira_username in self.pass_cache:
            return self.pass_cache[self.config_entry.jira_username]
        elif os.environ.get("TOGGL_JIRA_PASS", None):
            return os.environ["TOGGL_JIRA_PASS"]
        else:
            jira_pass = getpass(
                prompt="Jira password [{}]:".format(config_entry.jira_username)
            )
            self.pass_cache[self.config_entry.jira_username] = jira_pass
            return jira_pass

    def create(self):
        if self.config_entry.redmine_api_key:
            return RedmineHelper(
                config.redmine, config_entry.redmine_api_key, args.simulation
            )
        elif config_entry.jira_url:
            return JiraHelper(
                config_entry.jira_url,
                config_entry.jira_username,
                self.jira_pass,
                args.simulation,
            )
        else:
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Syncs toggle entries to redmine or jira. Version v{}".format(
            VERSION
        )
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

    # print("Found api key pairs: {}".format(len(config.entries)))

    mattermost = None

    if config.mattermost:
        runner = RequestsRunner.fromConfig(config.mattermost)
        mattermost = MattermostNotifier(runner, args.simulation)

    for config_entry in config.entries:
        print("Synchronization for {} ...".format(config_entry.label))
        print("---")
        toggl = TogglHelper(config.toggl, config_entry)
        api_helper = ApiHelperFactory(config_entry).create()
        if not api_helper:
            print(
                "Can't interpret config to destination API - entry: {}".format(
                    config_entry.label
                )
            )
            continue

        if mattermost != None:
            mattermost.append(
                "TogglSync v{} for {}".format(version.VERSION, config_entry.label)
            )
            mattermost.append("---")
            mattermost.append("")

        sync = Synchronizer(config, api_helper, toggl, mattermost)
        sync.start(args.days)

    if mattermost != None:
        mattermost.send()
