#!/usr/bin/env python3

import argparse
import os.path
import pickle
import re
import time
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
# Scope ot use if you want to do some test and you don't want to delete any
# events
# SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class EventDeletion:
    def __init__(self, time_min, time_max, confirm_delete=False):
        """
        The code to handle the authentification is a copy/paste from
        https://developers.google.com/calendar/quickstart/python
        """
        self.time_min = time_min
        self.time_max = time_max
        self.confirm_delete = confirm_delete
        self.deleted_events = set()

        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)

        self.service = build("calendar", "v3", credentials=creds)

    def delete_events(self):
        """Entry point to deletes all events from the calendar."""
        page_token = None

        while True:
            events = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=self.time_min.isoformat() + "Z",  # 'Z' indicates UTC time
                    timeMax=self.time_max.isoformat() + "Z",
                    maxResults=100,
                    singleEvents=True,
                    pageToken=page_token,
                    orderBy="startTime",
                )
                .execute()
            )

            for event in events["items"]:
                if self._is_recurrent(event):
                    rec_event = (
                        self.service.events()
                        .get(calendarId="primary", eventId=event["recurringEventId"])
                        .execute()
                    )
                    if self._event_is_passed(rec_event):
                        # If the event if part of a recurring event, and this event is
                        # passed, we also delete the recurring event which is kind of
                        # a "meta event".
                        self._delete_event(rec_event)

                if self._event_is_passed(event):
                    self._delete_event(event)

            page_token = events.get("nextPageToken")
            if not page_token:
                break

    def _is_recurrent(self, event):
        """Return True if the event is a recurrent event."""
        return "recurringEventId" in event

    def _event_is_passed(self, event):
        """Return True if the event is in our timeframe"""

        if "recurrence" in event:
            # https://tools.ietf.org/html/rfc5545#section-3.8.5
            for rec in event["recurrence"]:
                if "RRULE" in rec:
                    # Looking for: UNTIL=20170317T083000Z
                    result = re.search(r"UNTIL=(\d{8}T\d{6}Z)", rec, re.M)

                    if result:
                        until = datetime.strptime(result.group(1)[:13], "%Y%m%dT%H%M")
                        if until < self.time_max:
                            return True

            return False
        else:
            return self._get_datetime(event, "end") < self.time_max

    def _get_datetime(self, event, key="start"):
        """Return a datetime object for the start or end of the event."""

        if "dateTime" in event[key]:
            value = datetime.strptime(
                event[key].get("dateTime")[:19], "%Y-%m-%dT%H:%M:%S"
            )
        else:
            value = datetime.strptime(event[key].get("date"), "%Y-%m-%d")

        return value

    def _delete_event(self, event):
        """Delete the event if possible."""
        try:
            event_id = event["id"]

            if event_id in self.deleted_events:
                return

            if self.confirm_delete:
                time.sleep(0.1)  # To avoid rate limiting
                self.service.events().delete(
                    calendarId="primary", eventId=event_id, sendUpdates="none"
                ).execute()

            result = "DELETED"
            self.deleted_events.add(event_id)

        except HttpError as error:
            if error.resp.status == 410:
                # 410 - Resource has been deleted
                # Probably already deleted throught its parent recurrent event
                result = "ALREADY DELETED"
            else:
                print(error)
                result = "FAILED "
        except Exception as error:
            print(error)
            result = "FAILED "

        event_date = self._get_datetime(event)
        recurrent_tag = "[Recurent event] - " if "recurrence" in event else ""
        summary = event.get("summary", "").strip()
        print(f"{result} - {event_date} - {recurrent_tag}{summary}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm-delete",
        dest="confirm_delete",
        action="store_true",
        default=False,
        help="Confirm the event deletion. By default no events are deleted.",
    )
    parser.add_argument(
        "--delete-all",
        dest="delete_all",
        action="store_true",
        default=False,
        help=(
            "Will also delete events in the future. By default only passed"
            "events are deleted."
        ),
    )
    args = parser.parse_args()

    time_min = datetime.strptime("2000-01-01", "%Y-%m-%d")
    if args.delete_all:
        time_max = datetime.strptime("3000-01-01", "%Y-%m-%d")
    else:
        time_max = datetime.utcnow()

    print(
        f"This script will delete all events between "
        f"{time_min.strftime('%Y-%m-%d')} and {time_max.strftime('%Y-%m-%d')} "
        f"in your main calendar\n"
    )

    if not args.confirm_delete:
        print("*** Simulation mode - No event will be deleted ***\n")

    ed = EventDeletion(
        time_min=time_min, time_max=time_max, confirm_delete=args.confirm_delete,
    )
    ed.delete_events()

    print(
        f"\n{len(ed.deleted_events)} events has been moved to the trash. "
        f"Don't forget to empty it:\n"
        f"https://calendar.google.com/calendar/r/trash\n"
        f"Events in trash are automatically deleted after 30 days."
    )
