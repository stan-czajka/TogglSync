import requests
import json
from argparse import ArgumentParser
from datetime import datetime

from toggltoredmine.config import Config

class RequestsRunner:
    def send(self, url, data):
        requests.post(url, data=json.dumps(data))

class MattermostNotifier:
    def __init__(self, url, runner, simulation=False):
        self.url = url
        self.lines = []
        self.runner = runner
        self.simulation = simulation

    def append(self, message):
        self.lines.append(message)

    def appendEntries(self, allEntries):
        filteredEntries = [e for e in allEntries if e.taskId != None]

        self.append('Found entries in toggl: **{}** (with redmine id: **{}**)'.format(len(allEntries), len(filteredEntries)))

        entries = MattermostNotifier.filterToday(allEntries)

        timeSum = sum([e.duration for e in entries])

        if len(entries) == 0 or timeSum == 0:
            self.append('All together you did not work today at all :cry:. Hope you ok?')
        elif timeSum < 4 * 60 * 60: # 4 hours
            self.append('You worked almost less than 4 hours today (exactly {}), not every day is a perfect day, right? :smirk:.'.format(MattermostNotifier.formatSeconds(timeSum)))
        elif timeSum < 8 * 60 * 60: # 8 hours
            self.append('Hard day working today, yeah? You did good :clap:: {}.'.format(MattermostNotifier.formatSeconds(timeSum)))
        else:
            self.append('Wow you did overtime today :rocket:! Doing overtime from time to time can be good, but life after work is also important. Remember this next time taking {} in work :sunglasses:!'.format(MattermostNotifier.formatSeconds(timeSum)))

        if len(entries) > 0:
            if len(entries) < 5:
                self.append('Huh, not many entries. It means, you did only a couple of tasks, but did it right .. right? :open_mouth:')
            elif len(entries) < 20:
                self.append('Average day. Not too few, not too many entries :sunglasses:.')
            else:
                self.append('You did {} entries like a boss :smirk: :boom:!'.format(len(entries)))

        self.append('')

    def send(self):
        text = '\n'.join(self.lines)
        data = { 'text': text, 'username': 'toggl2redmine' }

        if self.simulation:
            print('Message to mattermost:')
            print('-----------------------------------')
            print(text)
            print('-----------------------------------')
        else:
            self.runner.send(self.url, data)

        self.lines = []

    @staticmethod
    def formatSeconds(seconds):
        if seconds < 60:
            return '{} s'.format(seconds)

        if seconds < 60 * 60:
            return '{} m'.format(round(seconds / 60))

        return '{0:.2f} h'.format(seconds / (60*60.0))

    @staticmethod
    def filterToday(entries):
        if not entries:
            return []

        today = datetime.strftime(datetime.today(), '%Y-%m-%d')
        return [e for e in entries if e.start and e.start.startswith(today)]


if __name__ == '__main__':
    parser = ArgumentParser(description='Sends notification to mattermost')

    parser.add_argument('-m', '--message', help='Message to send', required=True)
    parser.add_argument('-s', '--simulation', help='Simulation mode', action='store_true', default=False)

    config = Config.fromFile()

    if config.mattermost == None:
        raise Exception('No mattermost in config defined')

    args = parser.parse_args()

    notifier = MattermostNotifier(config.mattermost, RequestsRunner(), args.simulation)
    notifier.append(args.message)
    notifier.send()

    print('Sent')