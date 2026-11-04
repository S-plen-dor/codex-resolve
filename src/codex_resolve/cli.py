import argparse
import json
import sys
from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(description="Codex Resolve project records and read-only connection")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a new project directory")
    init.add_argument("directory")
    init.add_argument("--name", required=True)
    show = commands.add_parser("project-status", help="Read project records")
    show.add_argument("directory")
    snapshot = commands.add_parser("checkpoint", help="Snapshot project records, not the Resolve database")
    snapshot.add_argument("directory")
    snapshot.add_argument("--label", required=True)
    commands.add_parser("resolve-status", help="Read current Resolve state without modifying it")
    args = parser.parse_args(argv)
    try:
        if args.command == "resolve-status":
            from .resolve import status
            result = status()
        else:
            from .project import initialize, inspect, checkpoint
            if args.command == "init":
                result = initialize(args.directory, args.name)
            elif args.command == "checkpoint":
                result = checkpoint(args.directory, args.label)
            else:
                result = inspect(args.directory)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
