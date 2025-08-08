#!/usr/bin/env python3

# Read the instructions in the readme to configure credentials and scopes.

import os.path
import json
import argparse
from datetime import datetime
from email.utils import parsedate_to_datetime, parseaddr
import concurrent.futures
import tempfile

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the app directory in TMPDIR
APP_DIR = os.path.join(tempfile.gettempdir(), "gmail_checker")
os.makedirs(APP_DIR, exist_ok=True)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CLIENT_SECRET_FILE = os.environ.get('GMAIL_CHECKER_SECRET_PATH', os.path.join(os.environ['HOME'], '.mygmail_client_secret.json'))
FETCH_COUNT = int(os.environ.get('GMAIL_CHECKER_FETCH_COUNT', 10))
STORAGE_FILE = os.path.join(APP_DIR, "gmail.storage")
quiet = False


def get_service():
    """Gets an authorized Gmail API service instance."""
    creds = None
    token_path = os.path.join(APP_DIR, "token.json")
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def mark_last_message_as_read():
    """
    Saves the current timestamp to a file.
    """
    try:
        # Store the current time as a Unix timestamp in milliseconds
        current_timestamp_ms = int(datetime.now().timestamp() * 1000)
        with open(STORAGE_FILE, "w") as f:
            f.write(str(current_timestamp_ms))
        print(f"Marked as read up to timestamp: {current_timestamp_ms}")

    except Exception as e:
        print(f"An error occurred while marking as read: {e}")


def check_messages():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail messages.
    """
    service = get_service()

    last_timestamp = None
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            last_timestamp = f.read().strip()

    query_parts = ["is:important", "is:unread"]
    if last_timestamp:
        try:
            # Add 1 second to the timestamp to avoid showing the last message again
            query_parts.append(f"after:{(int(last_timestamp) // 1000) + 1}")
        except ValueError:
            print(f"Warning: Invalid timestamp found in {STORAGE_FILE}. Ignoring.")
            # Optionally, you could delete the file here:
            # os.remove(STORAGE_FILE)

    query = " ".join(query_parts)


    try:
        # Call the Gmail API
        results = (
            service.users().messages().list(userId="me", q=query, maxResults=FETCH_COUNT).execute()
        )
        messages = results.get("messages", [])

        if not messages:
            if not quiet:
                print("No new messages found.")
            return

        print(f"New messages: {len(messages)}")
        # show 1 message

        # print(json.dumps(service.users().messages().get(userId="me", id=messages[0]["id"]).execute()))
        return
        for message in messages:
            print(f'Message ID: {message["id"]}')
            msg = (
                service.users().messages().get(userId="me", id=message["id"]).execute()
            )
            print(f'  Subject: {msg["snippet"]}')

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")


def fetch_message_details(message):
    """Fetches and parses details for a single message."""
    service = get_service()  # Create a new service object for each thread
    msg = service.users().messages().get(userId="me", id=message["id"]).execute()
    headers = msg["payload"]["headers"]
    subject = next(
        (header["value"] for header in headers if header["name"] == "Subject"),
        "No Subject",
    )
    sender_header = next(
        (header["value"] for header in headers if header["name"] == "From"),
        "Unknown Sender",
    )
    name, addr = parseaddr(sender_header)
    sender = name or addr or "Unknown Sender"

    date_str = next(
        (header["value"] for header in headers if header["name"] == "Date"),
        None,
    )

    date_obj = "Unknown Date"
    if date_str:
        try:
            date_obj = parsedate_to_datetime(date_str).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    return sender, subject, date_obj


def list_messages():
    """Lists new messages since last saved check timestamp."""
    service = get_service()

    last_timestamp = None
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            last_timestamp = f.read().strip()

    query_parts = ["is:important", "is:unread"]
    if last_timestamp:
        try:
            # Add 1 second to the timestamp to avoid showing the last message again
            query_parts.append(f"after:{(int(last_timestamp) // 1000) + 1}")
        except ValueError:
            print(f"Warning: Invalid timestamp found in {STORAGE_FILE}. Ignoring.")

    query = " ".join(query_parts)

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=FETCH_COUNT)
            .execute()
        )
        messages = results.get("messages", [])

        if not messages:
            if not quiet:
                print("No new messages found.")
            return

        # print("New messages:")
        message_details = []
        max_sender_len = 0

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Each thread will create its own service object
            future_to_message = {
                executor.submit(fetch_message_details, message): message
                for message in messages
            }
            for future in concurrent.futures.as_completed(future_to_message):
                try:
                    sender, subject, date_obj = future.result()
                    message_details.append((sender, subject, date_obj))
                    if len(sender) > max_sender_len:
                        max_sender_len = len(sender)
                except Exception as exc:
                    print(f"Message generated an exception: {exc}")

        for sender, subject, date_obj in message_details:
            print(f"{sender:<{max_sender_len}} | {subject} | {date_obj}")

    except HttpError as error:
        print(f"An error occurred: {error}")


def unread_count():
    """Counts the number of unread messages based on the last check."""
    service = get_service()

    last_timestamp = None
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            last_timestamp = f.read().strip()

    query_parts = ["is:important", "is:unread"]
    if last_timestamp:
        try:
            # Add 1 second to the timestamp to avoid showing the last message again
            query_parts.append(f"after:{(int(last_timestamp) // 1000) + 1}")
        except ValueError:
            print(f"Warning: Invalid timestamp found in {STORAGE_FILE}. Ignoring.")

    query = " ".join(query_parts)

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=FETCH_COUNT)
            .execute()
        )
        messages = results.get("messages", [])
        print(len(messages))

    except HttpError as error:
        print(f"An error occurred: {error}")


def clear_read_status():
    """
    Removes the storage file to reset the 'read' status.
    """
    if os.path.exists(STORAGE_FILE):
        os.remove(STORAGE_FILE)
        print(f"Cleared read status. The next check will show all unread messages.")
    else:
        print("No read status to clear.")


def main():
    global quiet
    parser = argparse.ArgumentParser(
        description="A script to check Gmail messages.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["check", "help", "mark_as_read", "list", "clear_read", "unread_count"],
        default="help",
        help="""The command to run:
  check         - Check for new messages since last 'mark_as_read'.
  list          - List new messages.
  unread_count  - Show the count of new unread messages.
  mark_as_read  - Mark all current messages as read.
  clear_read    - Clear the 'read' status to see all messages again.
  help          - Display this help message.
""",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress informational output."
    )
    args = parser.parse_args()
    quiet = args.quiet

    if args.command == "check":
        check_messages()
    elif args.command == "mark_as_read":
        mark_last_message_as_read()
    elif args.command == "list":
        list_messages()
    elif args.command == "unread_count":
        unread_count()
    elif args.command == "clear_read":
        clear_read_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
