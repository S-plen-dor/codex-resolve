import argparse
import json
import sys
from . import __version__


def execute(args):
    if args.command == "skill-copy":
        from .installation import copy_skill
        return copy_skill(args.destination)
    if args.command == "resolve-capabilities":
        from .resolve import capabilities
        return capabilities()
    if args.command == "operation-check":
        from .execution import inspect_operation
        return inspect_operation(args.operation)
    if args.command == "produce":
        if args.changes and args.workspace:
            from .project import inspect
            from .plan import load_plan
            selected = inspect(args.workspace)['state.json'].get('plan_sha256')
            if selected and selected != load_plan(args.plan)['sha256']:
                raise ValueError('Feedback base differs from selected workspace plan')
        from .workflow import produce
        return produce(args.plan, args.out, args.project, args.timeline, args.preset,
                       args.save_current, args.start, args.changes, args.revision,
                       args.start_frame, args.end_frame, args.width, args.height)
    if args.command == "render-collect":
        from .delivery import collect
        return collect(args.record, args.out, args.file, args.qc, args.observe)
    if args.command == "review-record":
        from .delivery import review
        return review(args.collection, args.input, args.out)
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
            return render(args.operation, args.out, args.preset, args.start,
                          args.start_frame, args.end_frame, args.width, args.height)
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
    commands.add_parser("resolve-capabilities", help="Read available methods and render presets")
    skill = commands.add_parser("skill-copy", help="Copy bundled Skill into an explicitly chosen new folder")
    skill.add_argument("destination")
    check = commands.add_parser("operation-check", help="Compare a recorded work timeline with live Resolve")
    check.add_argument("operation")
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
    production = commands.add_parser("produce", help="Build a new version and queue/start a preview")
    production.add_argument("plan")
    production.add_argument("--project", required=True)
    production.add_argument("--timeline", required=True)
    production.add_argument("--out", required=True)
    production.add_argument("--preset", required=True)
    production.add_argument("--save-current", action="store_true", required=True)
    production.add_argument("--start", action="store_true")
    production.add_argument("--changes")
    production.add_argument("--revision")
    for command in (render, production):
        command.add_argument("--start-frame", type=int, default=0)
        command.add_argument("--end-frame", type=int)
        command.add_argument("--width", type=int)
        command.add_argument("--height", type=int)
    render_status = commands.add_parser("render-status", help="Read one recorded render job without waiting")
    render_status.add_argument("record")
    collect = commands.add_parser("render-collect", help="Associate a completed render file and optional QC/observations")
    collect.add_argument("record")
    collect.add_argument("--out", required=True)
    collect.add_argument("--file")
    collect.add_argument("--qc", action="store_true")
    collect.add_argument("--observe", action="store_true")
    review = commands.add_parser("review-record", help="Record supplied review evidence without inventing approval")
    review.add_argument("collection")
    review.add_argument("--input", required=True)
    review.add_argument("--out", required=True)
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
    for command in (observe, apply, render, render_status, revise, production, collect, review):
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
