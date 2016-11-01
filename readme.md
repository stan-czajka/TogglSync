Toggl2Redmine
===

`Toggl2Redmine` is an app for one way synchronizing **[toggl](toggl.com)** entries to **[redmine](https://www.redmine.org/)** time entries associated with **issues**. All toggl entries decorated with issue id (see example) will be treated as entries to send to redmine time entries.

Optionally after synchronization this app sends a notification to *mattermost*.

Example
---

I record a time entry and give it a comment: `Tracing bug for #345`. Running a `synchronizer` will insert a redmine time entry with comment `Tracing bug for #345 [toggl#0000]` at issue #345 (`[toggl#0000]` is a time entry decorator added by `synchronizer` to track unique toggl time entry id).

Issue id must start with hash sign (*#*) and can be placed anywhere in comment.

Requirements
---

* Toggl account and api key
* Redmine URL
* Redmine account and api key
* [Optional] *Mattermost* incoming webhook url

How to run
---

- Download pack from *releases* tab.
- Unpack ZIP package
- Copy `config.yml.example` to `config.yml`
- Fill `config.yml`

Usage
---

Get help:

```
synchronizer -h
```

Run synchronizer for last day:

```
synchronizer -d 1
```

Run synchronizer for last day in simulation mode:

```
synchronizer -d 1 -s
```

Mattermost
---

After synchronization a summary may be send to *mattermost*. In order to send notification you have to fill mattermost [incoming webhook](https://docs.mattermost.com/developer/webhooks-incoming.html) url in `config.yml`. After that *synchronizer* will send an short summary to mattermost.

You can also request *synchronizer* to post a message to particular channel. For that you have to fill `channel` key in `config.yml`. If you want to receive a message on default incoming webhook channel, remove this key from `config.yml`.

`channel` key in `config.yml` can be also a list and `Toggl2Redmine` will send a message to every specified channel. If you want to send a message to a particular channel and to default channel, add an empty channel and this particular one to `channel` list:

```
  channel: ["", "#channell"]
```

Development
---

**Prepare development environemnt**

```
python -m venv .env
.env\Scripts\activate.bat (or .sh)
pip install pybuilder
pyb install_dependencies
```

**Run tests**

```
nosetests -v
```

**Run tests with coverage**

```
nosetests --cover-html --with-coverage
```

**Prepare executable**

```
pyb build_exe
```
