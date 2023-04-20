from pathlib import Path
from watchdog.events import FileSystemEventHandler

from transpiler import transpile_file

class Watcher(FileSystemEventHandler):
    def __init__(self, source):
        self.source = source

    def on_any_event(self, event):
        if Path(event.src_path).match("*.py"):
            transpile_file(event.src_path)