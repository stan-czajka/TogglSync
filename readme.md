![Test Status](https://github.com/stan-czajka/TogglSync/workflows/Run%20Python%20Tests/badge.svg)

TogglSync
===

`TogglSync` is an app for one way synchronizing **[toggl](toggl.com)** entries to:
 - **[redmine](https://www.redmine.org/)** time entries associated with **issues**. 
 - **[jira]()** work log associated with Jira issue

All toggl entries decorated with issue id (see example) will be treated as entries to send to redmine time entries.

Optionally after synchronization this app sends a notification to *mattermost*.

Tracking entries in Toggl
---

Add a time entry in Toggl and give it a comment: 
- `Tracing bug for #345` (for redmine issue `#345`)
- `New time entry XYZ-123` (for Jira issue `XYZ-123`) 

Running a `synchronizer` will insert a redmine time entry with comment `Tracing bug for #345 [toggl#0000]` at issue #345. `[toggl#0000]` is a time entry decorator added by `synchronizer` to track unique toggl time entry id.

Time entry description must contain redmine issue id or jira issue slug in a proper format defined in config file.

Requirements
---

* Toggl account and api key
* For Redmine integration:
   - Redmine URL
   - Redmine account and api key
* For Jira integration:
   - Jira URL
   - Jira username and password
* [Optional] *Mattermost* incoming webhook url

How to run
---

- Download pack from *releases* tab.
- Unpack ZIP package
- Copy `config.yml.example` to `config.yml`
- Edit `config.yml`

**On Windows:**
- Run `synchronizer.exe` file with parameters

**On Mac OS X / Unix:**
- Prepare environment (see Advanced chapter)
- Run script from python (see Advanced chapter)
- Optionally prepare runnable script
   - use `examples/togglsync_last_day_simulation` (for OS X)
   - make file executable:
        ```
        chmod u+x examples/togglsync_last_day_simulation
        ```
   - edit the command parameters in file to run sync with proper attributes
   - rename file accordingly  

Examples  
---

Get help:

```
synchronizer --help
```

Run synchronizer for today:

```
synchronizer -d 0
```

Run synchronizer for today in simulation mode (no changes will be made):

```
synchronizer -d 0 -s
```

Mattermost
===

After synchronization a summary may be send to *mattermost*. In order to send notification you have to fill mattermost [incoming webhook](https://docs.mattermost.com/developer/webhooks-incoming.html) url in `config.yml`. After that *synchronizer* will send an short summary to mattermost.

You can also request *synchronizer* to post a message to particular channel. For that you have to fill `channel` key in `config.yml`. If you want to receive a message on default incoming webhook channel, remove this key from `config.yml`.

`channel` key in `config.yml` can be also a list and `TogglSync` will send a message to every specified channel. If you want to send a message to a particular channel and to default channel, add an empty channel and this particular one to `channel` list:

```
  channel: ["", "#channell"]
```

Advanced
===

**Prepare environment**

On Unix/OS X:
```
cd (to repo root)
virtualenv -p python3 .env (osx)
python3 -m pip install --upgrade pip
source .env/bin/activate
pip install -r requirements.txt
```

On Windows:
```
cd (to repo root)
python -m venv .env
python -m pip install --upgrade pip
.env\Scripts\activate.bat
pip install -r requirements.txt
```

**Run script from python**

On Unix/OS X:
```
cd (to repo root)
source .env/bin/activate
export PYTHONPATH=.
python togglsync/synchronizer.py --help
```

On Windows:
```
cd (to repo root)
.env\Scripts\activate.bat
set PYTHONPATH=.
python togglsync/synchronizer.py --help
```

**Run tests**

```
nosetests -v
```

**Run tests with coverage**

```
nosetests --with-coverage --cover-package togglsync
```

**Prepare executable**

```
pyinstaller --onefile --icon=icon.ico synchronizer.spec
```

Change log
---

**0.5.1**
- Integration with Jira

**0.5.2**
- Implemented rounding (to minutes) for Jira 
- Skipping zero-length entries
- Added colors to console output
- Added --errors switch and simplified error message 
- Added example script for OS X 

**0.5.3**
- Support for worklog from cloud Jira