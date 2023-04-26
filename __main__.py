import argparse
import time
import coloredlogs
import logging
import ast
import astpretty

from pathlib import Path
from watchdog.observers import Observer
from watcher import Watcher
from transpiler import Transpiler

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
debug = args.debug

def transpile():
    logging.info(f"Transpiling {source_directory}...")
    for source_file in Path(source_directory).rglob("*.py"):
        transpile_file(source_file)
    logging.info("Transpiled successfully.")

def transpile_file(source_file):
    logging.info(f"Transpiling {source_file}...")
    with open(source_file) as f:
        try:
            tree = ast.parse(f.read())

            if debug:
                astpretty.pprint(tree)

            transpiled = Transpiler().transpile(tree)
            dest_file = source_file.with_suffix(".cs")

            with open(dest_file, "w") as dest:
                dest.write(transpiled)
        except Exception as e:
            logging.exception(f"Caught error while transpiling {source_file}:", exc_info=e)
        else:
            logging.info(f"{source_file} has been transpiled.")

transpile()

if args.watch:
    observer = Observer()
    observer.schedule(Watcher(transpile), source_directory, True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()