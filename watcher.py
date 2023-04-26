from watchdog.events import PatternMatchingEventHandler

class Watcher(PatternMatchingEventHandler):
    def __init__(self, action):
        super().__init__(patterns=["*.py"])
        self.action = action

    def on_any_event(self, event):
        self.action()