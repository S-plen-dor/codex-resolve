"""Structural plan checks. These do not evaluate editing taste or connect to Resolve."""
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path


def integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def bounds(value, name):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(name + ' must be [start,end)')
    start, end = (integer(v, name) for v in value)
    if end <= start:
        raise ValueError(name + ' must have positive duration')
    return start, end


def load_plan(path):
    path = Path(path).expanduser().resolve(strict=True)
    raw = path.read_bytes()
    data = json.loads(raw)
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported schema_version')
    if not isinstance(data.get('revision'), str) or not data['revision'].strip():
        raise ValueError('Provide a nonempty revision')
    timeline = data['timeline']
    fps = Fraction(timeline['fps'])
    if fps <= 0:
        raise ValueError('Timeline fps must be positive')
    for field in ('width', 'height'):
        integer(timeline[field], field, 1)
    # Paths are relative to explicit project root, otherwise the plan directory.
    root = (path.parent / data.get('project_root', '.')).resolve(strict=True)
    sources = {}
    for source in data['sources']:
        key = source['id']
        if not isinstance(key, str) or not key or key in sources:
            raise ValueError('Source IDs must be unique nonempty strings')
        actual = (root / source['path']).expanduser().resolve(strict=True)
        source_rate = source.get('fps', timeline['fps'] if source.get('kind') == 'audio' else None)
        if not actual.is_file() or source_rate is None or Fraction(source_rate) <= 0:
            raise ValueError('Sources must be files with a positive fps')
        expected = source.get('sha256')
        if expected:
            h = hashlib.sha256()
            with actual.open('rb') as stream:
                for block in iter(lambda: stream.read(4*1024*1024), b''):
                    h.update(block)
            if expected != h.hexdigest():
                raise ValueError('Source content changed: '+key)
        sources[key] = {**source, 'fps': str(Fraction(source_rate)), 'absolute_path': str(actual)}
    if not sources:
        raise ValueError('At least one source is required')
    seen = set()
    tracks = {}
    duration = 0
    for shot in data['shots']:
        key = shot['id']
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('Shot IDs must be unique nonempty strings')
        seen.add(key)
        if shot['source_id'] not in sources:
            raise ValueError('Unknown source for '+key)
        bounds(shot['source_range'], key+' source_range')
        start, end = bounds(shot['timeline_range'], key+' timeline_range')
        track = integer(shot.get('track', 1), key+' track', 1)
        tracks.setdefault(track, []).append((start, end, key))
        duration = max(duration, end)
        if not isinstance(shot.get('effects', []), list):
            raise ValueError('effects must be a list')
    if not seen:
        raise ValueError('At least one shot is required')
    for clips in tracks.values():
        clips.sort()
        for left, right in zip(clips, clips[1:]):
            if right[0] < left[1]:
                raise ValueError('Same-track overlap requires an explicit transition adapter: '+right[2])
    audio = data.get('audio', [])
    if not isinstance(audio, list):
        raise ValueError('audio must be a list; use [] for intentionally silent output')
    audio_tracks = {}
    for item in audio:
        key = item['id']
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('Audio IDs must be nonempty and unique across all clips')
        seen.add(key)
        if item['source_id'] not in sources:
            raise ValueError('Unknown audio source')
        bounds(item['source_range'], key+' source_range')
        start, end = bounds(item['timeline_range'], key+' timeline_range')
        audio_tracks.setdefault(integer(item.get('track', 1), 'audio track', 1), []).append((start, end, key))
        duration = max(duration, end)
        if item.get('layout', 'stereo') not in ('mono', 'stereo'):
            raise ValueError('Current audio adapter supports mono/stereo tracks')
    for clips in audio_tracks.values():
        clips.sort()
        if any(b[0] < a[1] for a, b in zip(clips, clips[1:])):
            raise ValueError('Overlapping audio must use separate tracks')
    return {'path': str(path), 'root': str(root), 'sha256': hashlib.sha256(raw).hexdigest(),
            'data': data, 'sources': sources, 'duration_frames': duration}


def validate(path):
    plan = load_plan(path)
    return {'structurally_valid': True, 'plan_sha256': plan['sha256'],
            'duration_frames': plan['duration_frames'], 'revision': plan['data']['revision'],
            'scope': 'Structure, paths and optional source hashes only; not media decode, execution or aesthetic approval'}


def compare(before, after):
    old, new = load_plan(before), load_plan(after)
    def clips(plan):
        return {row['id']: row for group in ('shots', 'audio') for row in plan['data'].get(group, [])}
    a, b = clips(old), clips(new)
    return {'added': sorted(b.keys()-a.keys()), 'removed': sorted(a.keys()-b.keys()),
            'changed': sorted(k for k in a.keys() & b.keys() if a[k] != b[k]),
            'timeline_changed': old['data']['timeline'] != new['data']['timeline'],
            'sources_changed': old['data']['sources'] != new['data']['sources'],
            'scope': 'Plan comparison only; does not modify Resolve'}


def executable(plan):
    """Limits of the first adapter, not creative restrictions on plans."""
    data = plan['data']
    extra = set(data)-{'schema_version', 'status', 'revision', 'project_root', 'timeline',
                       'sources', 'shots', 'audio', 'notes', 'creative_brief'}
    if extra:
        raise ValueError('First executor does not implement plan fields: '+', '.join(sorted(extra)))
    fps = Fraction(data['timeline']['fps'])
    if set(data['timeline'])-{'fps', 'width', 'height'}:
        raise ValueError('First executor only handles fps/width/height timeline settings')
    for key in ('transitions', 'generators', 'color', 'retime'):
        if data.get(key):
            raise ValueError(key+' requires another adapter; no silent downgrade')
    for row in data['shots'] + data.get('audio', []):
        supported = {'id', 'source_id', 'source_range', 'timeline_range', 'track', 'reason',
                     'notes', 'effects', 'properties', 'layout', 'retime', 'gain_db',
                     'fade_in_frames', 'fade_out_frames'}
        extra = set(row)-supported
        if extra:
            raise ValueError('First executor does not implement clip fields: '+', '.join(sorted(extra)))
        if Fraction(plan['sources'][row['source_id']]['fps']) != fps:
            raise ValueError('First executor requires matching source/timeline rates')
        a, b = bounds(row['source_range'], 'source_range')
        c, d = bounds(row['timeline_range'], 'timeline_range')
        if b-a != d-c:
            raise ValueError('This adapter requires output-length source handles; retime maps within those handles')
        is_audio = row in data.get('audio', [])
        if is_audio:
            if row.get('retime') or row.get('effects') or row.get('properties'):
                raise ValueError('Audio uses gain_db/fades; video retime/effects need separate adapters')
            gain = row.get('gain_db', 0)
            if isinstance(gain, bool) or not isinstance(gain, (int, float)) or not math.isfinite(gain):
                raise ValueError('gain_db must be finite')
            for key in ('fade_in_frames', 'fade_out_frames'):
                if integer(row.get(key, 0), key) > d-c:
                    raise ValueError('Audio fade exceeds clip duration')
        else:
            if any(k in row for k in ('gain_db', 'fade_in_frames', 'fade_out_frames')):
                raise ValueError('Audio parameters belong to audio clips')
            from .effects import validate as validate_effects
            validate_effects(row, str(fps))
        for prop, value in row.get('properties', {}).items():
            if row in data.get('audio', []) or prop not in ('ZoomX', 'ZoomY', 'Pan', 'Tilt', 'RotationAngle', 'Opacity'):
                raise ValueError('Unsupported clip property: '+prop)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('Clip properties require finite numeric values')
            if prop in ('ZoomX', 'ZoomY') and value <= 0:
                raise ValueError('Zoom must be positive')
            if prop == 'Opacity' and not 0 <= value <= 100:
                raise ValueError('Opacity must be within Resolve range 0..100')
    layouts = {}
    for row in data.get('audio', []):
        track = row.get('track', 1)
        layout = row.get('layout', 'stereo')
        if track in layouts and layouts[track] != layout:
            raise ValueError('Conflicting audio layouts on one track')
        layouts[track] = layout
    return plan
