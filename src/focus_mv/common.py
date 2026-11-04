import hashlib
import json
import math
import subprocess
import sys
import platform
import os
import shutil
from fractions import Fraction
from pathlib import Path

from . import __version__

ROOT = Path(__file__).resolve().parents[2]


def environment():
    """Resolve portable configuration without importing historical runtimes."""
    selected = os.environ.get('CODEX_RESOLVE_CONFIG')
    config_path = Path(selected).expanduser().resolve() if selected else Path.cwd() / 'environment.local.json'
    config = {}
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    elif selected:
        raise ValueError('CODEX_RESOLVE_CONFIG does not exist: ' + str(config_path))
    requested = os.environ.get('CODEX_RESOLVE_FFMPEG') or config.get('ffmpeg') or 'ffmpeg'
    executable = shutil.which(requested)
    if not executable:
        candidate = Path(requested).expanduser()
        if not candidate.is_absolute():
            candidate = config_path.parent / candidate
        if candidate.is_file():
            executable = str(candidate.resolve())
    if not executable:
        raise ValueError('FFmpeg not found. Add it to PATH or set CODEX_RESOLVE_FFMPEG.')
    model = os.environ.get('CODEX_RESOLVE_ASR_MODEL') or config.get('asr_model')
    if model:
        model_path = Path(model).expanduser()
        if not model_path.is_absolute():
            model_path = config_path.parent / model_path
        model = str(model_path.resolve())
    return {'python': sys.executable, 'ffmpeg': executable, 'asr_model': model}


def run_ffmpeg(args, *, input=None, timeout=None):
    config = environment()
    command = [config['ffmpeg'], '-hide_banner', '-nostdin', *map(str, args)]
    result = subprocess.run(command, input=input, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('FFmpeg failed: ' + result.stderr.decode('utf-8', errors='replace')[-6000:])
    return result


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(path):
    path = Path(path).resolve(strict=True)
    info = path.stat()
    digest = sha256(path)
    after = path.stat()
    if (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Input changed while hashing: ' + str(path))
    return {'path': str(path), 'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns, 'sha256': digest}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def fresh_output(path, inputs=()):
    path = Path(path).resolve()
    if path.exists():
        raise FileExistsError('Output already exists: ' + str(path))
    if path in {Path(p).resolve() for p in inputs}:
        raise ValueError('Output cannot replace an input')
    return path


def make_report(tool, inputs, parameters, resource_paths=()):
    sources = [identity(p) for p in inputs]
    resources = [identity(p) for p in resource_paths]
    ffmpeg_version = run_ffmpeg(['-version']).stdout.decode(errors='replace').splitlines()[0]
    # Paths and mtimes are provenance, not cache identity: relocation should not invalidate content.
    implementation = hashlib.sha256()
    for source in sorted(Path(__file__).resolve().parent.glob('*.py')):
        implementation.update(source.name.encode());implementation.update(source.read_bytes())
    spec = {'tool': tool, 'toolkit_version': __version__, 'implementation_sha256':implementation.hexdigest(),
            'python_version':platform.python_version(), 'environment_sha256':hashlib.sha256(json.dumps(environment(), sort_keys=True).encode()).hexdigest(),
            'inputs_sha256': [s['sha256'] for s in sources], 'resources_sha256':[s['sha256'] for s in resources],
            'parameters': parameters, 'ffmpeg': ffmpeg_version}
    digest = hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {'schema_version': 1, **spec, 'cache_key': digest, 'sources': sources, 'resources':resources}


def check_cache(path, inputs=None):
    report=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    paths=inputs or [s['path'] for s in report['sources']]
    expected=make_report(report['tool'],paths,report['parameters'],[r['path'] for r in report.get('resources',[])])
    reasons=[]
    if expected['cache_key']!=report['cache_key']:reasons.append('Input, parameters, code, runtime or FFmpeg changed')
    if report.get('passed') is False:reasons.append('Previous check failed')
    base=Path(path).resolve().parent
    artifacts=[]
    if report['tool'] in ('media.frames','media.paired_frames'):
        artifacts=[(base/f['file'],f['sha256']) for f in report['frames']]
        artifacts.append((base/report['sheet'],report['sheet_sha256']))
    if report['tool']=='media.cover':artifacts=[(Path(report['output']),report['output_sha256'])]
    artifacts.extend((base/a['file'],a['sha256']) for a in report.get('artifacts',[]))
    for target,digest in artifacts:
        if not target.is_file() or sha256(target)!=digest:reasons.append('Missing or changed artifact: '+str(target))
    return {'passed':not reasons,'reusable':not reasons,'cache_key':report['cache_key'],'reasons':reasons,
            'report':str(Path(path).resolve()),'scope':'Checks content identity and generated artifact hashes; does not upgrade the original review scope.'}


def finite(value, name):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(name + ' must be finite')
    return value


def rate(value):
    value = Fraction(value)
    if value <= 0:
        raise ValueError('Frame rate must be positive')
    return value
