import argparse
import time
import coloredlogs

from watchdog.observers import Observer
from watcher import Watcher
from transpiler import transpile_directory

coloredlogs.install(fmt="%(asctime)s - %(levelname)s - %(message)s")

parser = argparse.ArgumentParser(
    prog="punity",
    description="Python -> C# transpiler developed with Unity in mind"
)

parser.add_argument("source")
parser.add_argument("-o", "--output")
parser.add_argument("-w", "--watch", action="store_true")
parser.add_argument("-d", "--debug", action="store_true")

args = parser.parse_args()

source_directory = args.source

transpile_directory(source_directory)

if args.watch:
    observer = Observer()
    observer.schedule(Watcher(source_directory), source_directory, True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()