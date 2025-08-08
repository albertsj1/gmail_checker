# Gmail Checker

This script provides a command-line interface to check for new messages in a Gmail account.  I use it with [SketchyBar](https://github.com/FelixKratz/SketchyBar) in a custom plugin to show how many unread messages I have and a list on hover.  There is a `mark_as_read` functionality; however, it does not actually mark the email as read.  It simply hides those emails and future checks will only show new emails since you last ran the `mark_as_read` command.

## Installation

This project uses `uv` for package management.

1.  **Install uv:**

    Follow the official instructions to install `uv` on your system:

    **On OSX:**
    ```bash
    brew install uv
    ```

    **Other:**

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Install Dependencies:**

    Once `uv` is installed, you can install the project dependencies from `pyproject.toml`:
    ```bash
    uv sync
    ```

## First-Time Setup

Before you can use this script, you need to enable the Gmail API and download a `client_secret.json` file.

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project.
3.  Enable the "Gmail API" for your project.
4.  Create credentials for a "Desktop app".
5.  Download the JSON file and save it in your home directory with the name `.mygmail_client_secret.json`.  If you'd like to use a custom location, set `GMAIL_CHECKER_SECRET_PATH` to the location of the secrets file.

The first time you run the script, it will open a browser window and ask you to authorize access to your Gmail account. After you grant permission, it will save a `token.json` file in a temporary directory, and you won't have to authorize it again until that temporary directory is delete.  Temp dir cleanup is determined by your OS settings.

## Usage

You can run the script with the following commands:

**If inside the project directory:**
```bash
uv run main.py [command]
```

**To run from any directory:**
```bash
uv run --project ~/<project_path> ~/<project_path>/main.py [command]
```

The default is only show the last 10 unread.  This can be customized by setting a `GMAIL_CHECKER_FETCH_COUNT` variable.

### Available Commands

```bash
usage: main.py [-h] [-q] [{check,help,mark_as_read,list,clear_read,unread_count}]

A script to check Gmail messages.

positional arguments:
  {check,help,mark_as_read,list,clear_read,unread_count}
                        The command to run:
                          check         - Check for new messages since last 'mark_as_read'.
                          list          - List new messages.
                          unread_count  - Show the count of new unread messages.
                          mark_as_read  - Mark all current messages as read.
                          clear_read    - Clear the 'read' status to see all messages again.
                          help          - Display this help message.

options:
  -h, --help            show this help message and exit
  -q, --quiet           Suppress informational output.
```

If you run the script with no command, it will default to showing the help message.

