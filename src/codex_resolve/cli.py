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
    observe = commands.add_parser("observe", help="Create frame evidence and an optional short review clip")
    observe.add_argument("source")
    observe.add_argument("--out", required=True)
    observe.add_argument("--start", type=int, default=0)
    observe.add_argument("--end", type=int)
    observe.add_argument("--interval", type=float, default=5.0)
    observe.add_argument("--width", type=int, default=360)
    observe.add_argument("--clip", action="store_true")
    validate = commands.add_parser("plan-validate", help="Check plan structure and local sources without Resolve")
    validate.add_argument("plan")
    diff = commands.add_parser("plan-diff", help="Compare stable clip IDs across two plans")
    diff.add_argument("before")
    diff.add_argument("after")
    apply = commands.add_parser("plan-apply", help="Save/backup current project and build a NEW work timeline")
    apply.add_argument("plan")
    apply.add_argument("--project", required=True)
    apply.add_argument("--timeline", required=True)
    apply.add_argument("--out", required=True)
    apply.add_argument("--save-current", action="store_true", required=True)
    render = commands.add_parser("render-submit", help="Queue a preset-based preview of an apply operation")
    render.add_argument("operation")
    render.add_argument("--out", required=True)
    render.add_argument("--preset", required=True)
    render.add_argument("--start", action="store_true")
    render_status = commands.add_parser("render-status", help="Read one recorded render job without waiting")
    render_status.add_argument("record")
    args = parser.parse_args(argv)
    try:
        if args.command == "observe":
            from .observe import observe
            result = observe(args.source, args.out, args.start, args.end, args.interval, args.width, args.clip)
        elif args.command in ("plan-validate", "plan-diff"):
            from .plan import validate, compare
            result = validate(args.plan) if args.command == "plan-validate" else compare(args.before, args.after)
        elif args.command in ("plan-apply", "render-submit", "render-status"):
            from .execution import apply, render, render_status
            if args.command == "plan-apply":
                result = apply(args.plan, args.project, args.timeline, args.out, args.save_current)
            elif args.command == "render-submit":
                result = render(args.operation, args.out, args.preset, args.start)
            else:
                result = render_status(args.record)
        elif args.command == "resolve-status":
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
