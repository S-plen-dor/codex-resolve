import argparse
import json
import sys
from . import __version__


def execute(args):
    if args.command == "observe":
        from .observe import observe
        return observe(args.source, args.out, args.start, args.end, args.interval, args.width, args.clip)
    if args.command in ("plan-validate", "plan-diff", "plan-register"):
        from .plan import validate, compare, load_plan
        if args.command == "plan-register":
            plan = load_plan(args.plan)
            return {'plan': plan['path'], 'plan_sha256': plan['sha256'],
                    'revision': plan['data']['revision'], 'scope': 'Selected plan; not executed or reviewed'}
        return validate(args.plan) if args.command == "plan-validate" else compare(args.before, args.after)
    if args.command in ("plan-locate", "plan-revise"):
        from .revision import locate, revise
        if args.command == "plan-locate":
            return locate(args.plan, args.start, args.end)
        if args.workspace:
            from .project import inspect
            from .plan import load_plan
            current = inspect(args.workspace)['state.json'].get('plan_sha256')
            if current and current != load_plan(args.plan)['sha256']:
                raise ValueError('Revision base is not the current workspace plan; select the intended base explicitly')
        return revise(args.plan, args.changes, args.out, args.revision)
    if args.command in ("plan-apply", "render-submit", "render-status"):
        from .execution import apply, render, render_status
        if args.command == "plan-apply":
            return apply(args.plan, args.project, args.timeline, args.out, args.save_current)
        if args.command == "render-submit":
            return render(args.operation, args.out, args.preset, args.start)
        return render_status(args.record)
    if args.command == "resolve-status":
        from .resolve import status
        return status()
    if args.command == "resume":
        from .session import resume
        return resume(args.directory)
    from .project import initialize, inspect, checkpoint
    if args.command == "init":
        return initialize(args.directory, args.name)
    if args.command == "checkpoint":
        return checkpoint(args.directory, args.label)
    return inspect(args.directory)


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
    register = commands.add_parser("plan-register", help="Select an existing plan in project state")
    register.add_argument("plan")
    register.add_argument("--workspace", required=True)
    locate = commands.add_parser("plan-locate", help="Find clip IDs overlapping timeline frames")
    locate.add_argument("plan")
    locate.add_argument("--start", type=int, required=True)
    locate.add_argument("--end", type=int)
    revise = commands.add_parser("plan-revise", help="Apply agent-authored clip changes to a new plan version")
    revise.add_argument("plan")
    revise.add_argument("--changes", required=True)
    revise.add_argument("--out", required=True)
    revise.add_argument("--revision", required=True)
    resume = commands.add_parser("resume", help="Read project context and missing artifact paths")
    resume.add_argument("directory")
    for command in (observe, apply, render, render_status, revise):
        command.add_argument("--workspace", help="Initialized project directory; track history and update handoff")
    args = parser.parse_args(argv)
    try:
        from .session import run
        result = run(args, lambda: execute(args))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
