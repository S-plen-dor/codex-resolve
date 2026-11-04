"""Project records; no Resolve connection or media modification."""
import json
from datetime import datetime, timezone
from pathlib import Path


def write_new(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def initialize(root, name):
    root = Path(root).expanduser().resolve()
    if root.exists():
        raise ValueError("Choose a new project directory; existing directories are not modified")
    if not name.strip():
        raise ValueError("Project name cannot be empty")
    root.mkdir(parents=True)
    for child in ("analysis", "plans", "assets", "renders", "versions"):
        (root / child).mkdir()
    record = {"schema_version": 1, "name": name, "sources": [],
              "output": {"width": None, "height": None, "fps": None},
              "master_audio": None, "input_color_state": "unknown",
              "resolve": {"project_name": None, "timeline_name": None}}
    write_new(root / "project.json", record)
    write_new(root / "state.json", {"schema_version": 1, "stage": "intake",
              "current_plan": None, "current_render": None,
              "accepted_decisions": [], "pending_questions": [], "next_action": "Inspect supplied media"})
    (root / "HANDOFF.md").write_text(
        "# Project handoff\n\nRead project.json and state.json first.\n"
        "Record the latest user request, accepted decisions, current timeline, "
        "preview path, unresolved issues and next action here.\n", encoding="utf-8")
    (root / "creative-brief.md").write_text(
        "# Creative brief\n\n## User intent\n\n## References and their relevance\n\n"
        "## Current creative decisions (revisable)\n\n## Open creative questions\n\n"
        "No global house style. Record only this project's intent and decisions.\n", encoding="utf-8")
    return {"project_root": str(root), "created": True}


def inspect(root):
    root = Path(root).expanduser().resolve(strict=True)
    return {name: json.loads((root / name).read_text(encoding="utf-8"))
            for name in ("project.json", "state.json")}


def checkpoint(root, label):
    root = Path(root).expanduser().resolve(strict=True)
    inspect(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = root / "versions" / stamp
    target.mkdir()
    # Record text history only: this does not back up the Resolve database or media.
    for name in ("project.json", "state.json", "HANDOFF.md"):
        path = root / name
        if path.is_file():
            (target / name).write_bytes(path.read_bytes())
    write_new(target / "checkpoint.json", {"label": label, "created_utc": stamp,
              "scope": "project records only; Resolve DRP export and plan snapshots are separate"})
    return {"checkpoint": str(target), "scope": "project records only"}
