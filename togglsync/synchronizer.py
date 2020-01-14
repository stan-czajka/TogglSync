import argparse
import sys
import traceback
from getpass import getpass

import dateutil.parser

from togglsync import version
from togglsync.config import Config
from togglsync.jira_wrapper import JiraHelper
from togglsync.mattermost import MattermostNotifier, RequestsRunner
from togglsync.redmine_wrapper import RedmineHelper
from togglsync.toggl import TogglHelper
from togglsync.version import VERSION


class Synchronizer:
    def __init__(self, config, api_helper, toggl, mattermost):
        self.config = config
        self.api_helper = api_helper
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
                redmineEntries = list(self.api_helper.get(issueId))
                filteredRedmineEntries = [
                    e for e in redmineEntries if e.toggl_id != None
                ]

                print(
                    "Found entries in destination for issue {}: {} (with toggl id: {})".format(
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
        data = self.api_helper.dictFromTogglEntry(togglEntry)
        self.api_helper.put(**data)
        self.inserted += 1

    def __update_redmine_entry(self, togglEntry, redmineEntry):
        if self._equal(togglEntry, redmineEntry):
            print("\tUp to date: {}".format(togglEntry))
            self.skipped += 1
        else:
            print("\tEntry changed, updating in destination: {}".format(togglEntry))
            data = self.api_helper.dictFromTogglEntry(togglEntry)
            self.api_helper.update(id=redmineEntry.id, **data)
            self.updated += 1

    def __remove_redmine_entries(self, redmineEntries):
        for e in redmineEntries:
            self.api_helper.delete(e.id)
            print("\tRemoved in destination: {}".format(e))

    def _equal(self, togglEntry, redmineEntry):
        togglEntryDict = self.api_helper.dictFromTogglEntry(togglEntry)

        if togglEntryDict["issueId"] != redmineEntry.issue:
            print(
                '\tentries not equal, issueId: "{}" vs "{}"'.format(
                    togglEntryDict["issueId"], redmineEntry.issue
                )
            )
            return False

        # when comapring by seconds, accuracy has to be rounded to minutes
        # Jira API rounds/truncates to minutes event though data is provided in seconds
        if "seconds" in togglEntryDict and not self._eq_to_minutes(togglEntryDict["seconds"], redmineEntry.seconds):
            print(
                '\tentries not equal, seconds (accuracy to minutes): "{}" vs "{}"'.format(
                    togglEntryDict["seconds"], redmineEntry.seconds
                )
            )
            return False

        if "started" in togglEntryDict and not self._eq_datetime_str(togglEntryDict["started"], redmineEntry.spent_on):
            print(
                '\tentries not equal, started: "{}" vs "{}"'.format(
                    togglEntryDict["started"], redmineEntry.spent_on
                )
            )
            return False

        if "spentOn" in togglEntryDict and togglEntryDict["spentOn"] != redmineEntry.spent_on:
            print(
                '\tentries not equal, spentOn: "{}" vs "{}"'.format(
                    togglEntryDict["spentOn"], redmineEntry.spent_on
                )
            )
            return False

        if "hours" in togglEntryDict and togglEntryDict["hours"] != redmineEntry.hours:
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

    @staticmethod
    def _eq_to_minutes(source_seconds, target_seconds):
        return abs(source_seconds - target_seconds) < 60

    @staticmethod
    def _eq_datetime_str(source_time: str, target_time: str):
        # comparing wo/ microseconds
        source = dateutil.parser.parse(source_time).replace(microsecond=0)
        target = dateutil.parser.parse(target_time).replace(microsecond=0)
        return source == target



def create_api_helper():
    if config_entry.redmine_api_key:
        return RedmineHelper(config.redmine, config_entry.redmine_api_key, args.simulation)
    elif config_entry.jira_url:
        jira_pass = getpass(prompt="Jira password [{}]:".format(config_entry.jira_username))
        return JiraHelper(config_entry.jira_url, config_entry.jira_username, jira_pass, args.simulation)
    else:
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Syncs toggle entries to redmine or jira. Version v{}".format(VERSION)
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
        toggl = TogglHelper(config.toggl, config_entry)
        api_helper = create_api_helper()
        if not api_helper:
            print("Can't interpret config to destination API - entry: ".format(config_entry.label))
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
