import requests
import json
from argparse import ArgumentParser
from datetime import datetime

from toggltoredmine.config import Config
from toggltoredmine.toggl import TogglHelper

class RequestsRunner:
    """
    Class for sending requests at particular URL
    https://docs.mattermost.com/developer/webhooks-incoming.html
    """
    def __init__(self, url, channel=None, username=None):
        self.url = url
        self.channel = channel
        self.username = username

    @classmethod
    def fromConfig(cls, mattermostConfig):
        return cls(mattermostConfig['url'],
            mattermostConfig['channel'] if 'channel' in mattermostConfig else None,
            'toggl2redmine')

    def send(self, text):
        data = { 'text': text }

        if self.username:
            data['username'] = self.username
            print('Username: {}'.format(self.username))

        if self.channel:
            data['channel'] = self.channel
            print('Channel: {}'.format(self.channel))

        resp = requests.post(self.url, data=json.dumps(data, sort_keys=True))

        if resp.status_code != 200:
            try:
                j = resp.json()

                message = (j['message'] + '\n') if 'message' in j else ''
                message = j['detailed_error'] if 'detailed_error' in j else ''

                if len(message) == 0:
                    message = resp.text
            except:
                message = resp.text

            raise Exception('Error sending to mattermost:\n{}'.format(message))

class MattermostNotifier:
    def __init__(self, runner, simulation=False):
        self.lines = []
        self.runner = runner
        self.simulation = simulation

    def append(self, message):
        self.lines.append(message)

    def appendDuration(self, days):
        self.append('Sync: {} day{}'.format(days, 's' if days != 1 else ''))

    def appendEntries(self, allEntries):
        filteredAllEntries = TogglHelper.filterRedmineEntries(allEntries)

        self.append('Found entries in toggl: **{}** (filtered: **{}**)'.format(len(allEntries), len(filteredAllEntries)))

        entries = MattermostNotifier.filterToday(allEntries)

        timeSum = sum([e.duration for e in entries])

        if len(entries) == 0 or timeSum == 0:
            self.append('Altogether you did not work today at all :cry:. Hope you ok?')
        else:
            if timeSum < 4 * 60 * 60: # 4 hours
                self.append('You worked almost less than 4 hours today (exactly {}), not every day is a perfect day, right? :smirk:.'.format(MattermostNotifier.formatSeconds(timeSum)))
            elif timeSum < 8 * 60 * 60: # 8 hours
                self.append('Hard day working today, yeah? You did good :clap:: {}.'.format(MattermostNotifier.formatSeconds(timeSum)))
            else:
                self.append('Wow you did overtime today :rocket:! Doing overtime from time to time can be good, but life after work is also important. Remember this next time taking {} in work :sunglasses:!'.format(MattermostNotifier.formatSeconds(timeSum)))

            if len(entries) < 5:
                self.append('Huh, not many entries. It means, you did only a couple of tasks, but did it right .. right? :open_mouth:')
            elif len(entries) < 20:
                self.append('Average day. Not too few, not too many entries :sunglasses:.')
            else:
                self.append('You did {} entries like a boss :smirk: :boom:!'.format(len(entries)))

            redmineTodayEntries = MattermostNotifier.filterWithRedmineId(entries)

            factor = len(redmineTodayEntries) / len(entries)

            if factor < .25:
                self.append('Ugh. Less than 25% of your work had redmine id. Not so good :cry:.'.format())
            elif factor < .50:
                self.append('Almost 50% of your today work had redmine id :blush:.'.format())
            elif factor < .75:
                self.append("It's gooood. A lot of today work had redmine id! Congrats :sunglasses:.")
            else:
                self.append('It seems that more than 75% of your today work had redmine id! So .. you rock :rocket:!')

        self.append('')

    def send(self):
        text = '\n'.join(self.lines)

        if self.simulation:
            print('Message to mattermost:')
            print('-----------------------------------')
            print(text)
            print('-----------------------------------')
        else:
            self.runner.send(data)
            print('Sent to mattermost:')
            print(text)

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
        return [e for e in entries if e.start and e.start.startswith(today) and e.duration > 0]

    @staticmethod
    def filterWithRedmineId(entries):
        """Filters given entries according to taskId"""
        return [e for e in entries if e.taskId != None]

if __name__ == '__main__':
    parser = ArgumentParser(description='Sends notification to mattermost')

    parser.add_argument('-m', '--message', help='Message to send', required=True)
    parser.add_argument('-s', '--simulation', help='Simulation mode', action='store_true', default=False)

    config = Config.fromFile()

    if config.mattermost == None:
        raise Exception('No mattermost in config defined')

    args = parser.parse_args()

    runner = RequestsRunner.fromConfig(config.mattermost)

    notifier = MattermostNotifier(runner, args.simulation)
    notifier.append(args.message)
    notifier.send()

    print('Sent')
