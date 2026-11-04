"""Read-only connection adapter using the user's installed Resolve API module."""
import importlib
import os
import sys
from pathlib import Path


def connect():
    configured = os.environ.get("RESOLVE_SCRIPT_API")
    candidates = []
    if configured:
        candidates.extend([Path(configured) / "Modules", Path(configured)])
    if sys.platform == "win32":
        candidates.append(Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) /
                          "Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting/Modules")
    elif sys.platform == "darwin":
        candidates.append(Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"))
    else:
        candidates.append(Path("/opt/resolve/Developer/Scripting/Modules"))
    for folder in candidates:
        if (folder / "DaVinciResolveScript.py").is_file():
            sys.path.insert(0, str(folder))
            break
    try:
        module = importlib.import_module("DaVinciResolveScript")
        resolve = module.scriptapp("Resolve")
    except Exception as exc:
        raise RuntimeError("Cannot load the installed Resolve scripting bridge. Check RESOLVE_SCRIPT_API, "
                           "RESOLVE_SCRIPT_LIB and Python compatibility. " + str(exc)) from exc
    if not resolve:
        raise RuntimeError("Resolve is unavailable. Open Resolve Studio and enable external scripting: Local")
    return resolve


def status():
    resolve = connect()
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    timeline = project.GetCurrentTimeline() if project else None
    return {"version": resolve.GetVersionString(),
            "project": project.GetName() if project else None,
            "rendering": project.IsRenderingInProgress() if project else None,
            "timeline": {"name": timeline.GetName(), "start_frame": timeline.GetStartFrame(),
                         "end_frame": timeline.GetEndFrame(),
                         "video_tracks": timeline.GetTrackCount("video"),
                         "audio_tracks": timeline.GetTrackCount("audio")} if timeline else None,
            "scope": "read-only state; connection is not an editing capability test"}
