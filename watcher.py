from pathlib import Path
from watchdog.events import FileSystemEventHandler

class Watcher(FileSystemEventHandler):
    def __init__(self, action):
        self.action = action

    def on_any_event(self, event):
        if Path(event.src_path).match("*.py"):
            self.action()