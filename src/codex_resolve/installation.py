"""Copy the bundled Skill to an explicitly chosen new directory."""
import shutil
import sys
from pathlib import Path


def copy_skill(destination):
    candidates = [Path(__file__).resolve().parents[2]/'skills'/'resolve-edit',
                  Path(sys.prefix)/'share'/'codex-resolve'/'skills'/'resolve-edit']
    source = next((p for p in candidates if (p/'SKILL.md').is_file()), None)
    if source is None:
        raise ValueError('Bundled Skill not found; use the source repository skills/resolve-edit directory')
    target = Path(destination).expanduser().resolve()
    if target.exists():
        raise ValueError('Destination exists; existing user Skills are never overwritten')
    shutil.copytree(source, target)
    return {'skill_directory': str(target), 'scope': 'Copied files only; reload Codex to discover the Skill'}
