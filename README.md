# Google Calendar events deletion

This script helps you to delete your Google Calendar passed events.


## Getting Started

### Set up Google Calendar API credentials
- Go to [https://developers.google.com/calendar/quickstart/python](https://developers.google.com/calendar/quickstart/python)
- Click on "Enable the Google Calendar API" and choose "Desktop app"
- Click on "Download client configuration" and save the file `credentials.json` next to the python script.

### Installion

```
python -m pip install -r requirements.txt
```

### Usage

For the first time run the script without any parameters in order authenticate yourself.
```
python events_deletion.py
```

Parameters:
- `--confirm-delete`: Confirm the deletion of events. If omitted, the script does not delete any events.
- `--delete-all`: Delete all your events. If omitted, the script delete only passed events.


## License

See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
