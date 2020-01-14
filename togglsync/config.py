import os

from yaml import safe_load


class Entry:
    def __init__(
        self,
        label,
        redmine_api_key=None,
        toggl_api_key=None,
        jira_username=None,
        jira_url=None,
        task_patterns=None,
    ):
        self.label = label
        self.redmine_api_key = redmine_api_key
        self.toggl = toggl_api_key
        self.jira_username = jira_username
        self.jira_url = jira_url
        self.task_patterns = task_patterns

    def __str__(self):
        if self.redmine_api_key:
            return "{}: {}".format(self.toggl, self.redmine_api_key)
        else:
            return "{}: {}@{}".format(self.toggl, self.jira_username, self.jira_url)


class Config:
    def __init__(self, toggl, redmine, entries, mattermost):
        self.toggl = toggl
        self.redmine = redmine
        self.entries = entries
        self.mattermost = mattermost

    @classmethod
    def fromFile(cls, path="config.yml"):
        if not os.path.exists(path):
            raise Exception(
                "File {} does not exist. Check out config.yml.example and create config.yml".format(
                    path
                )
            )

        with open(path) as input:
            return Config.fromYml(input)

    @classmethod
    def fromYml(cls, yml):
        deserialized = safe_load(yml)

        if "toggl" not in deserialized:
            raise Exception('"toggl" element not found in config')

        toggl = deserialized["toggl"]

        redmine = deserialized.get("redmine", None)

        if "mattermost" in deserialized:
            if isinstance(deserialized["mattermost"], str):
                print("Warning: old config format")

                mattermost = {"url": deserialized["mattermost"]}
            else:
                mattermost = deserialized["mattermost"]

                if "url" not in mattermost:
                    raise Exception('Expected "url" param in "mattermost" section')

        else:
            mattermost = None

        if "entries" not in deserialized:
            raise Exception('"entries" element not found in config')

        entries = []

        for entry in deserialized["entries"]:
            entries.append(Entry(**entry))

        return cls(toggl, redmine, entries, mattermost)

    def __str__(self):
        return """config:
\ttoggl url:\t{}
\tredmine url:\t{}

\tentries:
\t\t{}""".format(
            self.toggl, self.redmine, "\n\t\t".join([str(e) for e in self.entries])
        )


if __name__ == "__main__":
    config = Config()
    print(config)
