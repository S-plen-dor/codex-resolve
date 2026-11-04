"""Associate actual render files and declared review evidence with a plan."""
import hashlib
import json
from pathlib import Path

from .execution import render_status, save_record
from .project import write_new


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def collect(record_path, output, file=None, qc=False, observation=False):
    record_path = Path(record_path).expanduser().resolve(strict=True)
    record = json.loads(record_path.read_text(encoding='utf-8'))
    status = render_status(record_path)['status']
    label = status.get('JobStatus', '') if isinstance(status, dict) else str(status)
    if label.casefold() not in ('complete', 'completed'):
        raise ValueError('Render is not complete: '+label)
    directory = Path(record['output_directory']).resolve(strict=True)
    if file:
        media = Path(file).expanduser().resolve(strict=True)
        if not media.is_relative_to(directory):
            raise ValueError('Selected file must belong to this render directory')
    else:
        candidates = [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in
                      ('.mp4', '.mov', '.mxf', '.mkv', '.avi', '.webm')]
        if len(candidates) != 1:
            raise ValueError('Cannot identify one rendered file; provide --file explicitly')
        media = candidates[0]
    if not media.is_file() or not media.stat().st_size:
        raise ValueError('Rendered file is missing or empty')
    out = Path(output).expanduser().resolve()
    if out.exists():
        raise ValueError('Collection directory must be new')
    operation_path = Path(record['operation'])
    operation = json.loads(operation_path.read_text(encoding='utf-8'))
    plan = json.loads((operation_path.parent/'plan.json').read_text(encoding='utf-8'))
    out.mkdir(parents=True)
    manifest = out/'collection.json'
    result = {'kind': 'collection', 'render_record': str(record_path), 'operation': str(operation_path),
              'plan_sha256': operation['plan_sha256'], 'media': str(media), 'sha256': digest(media),
              'timeline_range': record.get('timeline_range', [0, operation['duration_frames']]),
              'qc': 'skipped', 'review': 'not_reviewed', 'status': 'collecting'}
    save_record(manifest, result)
    try:
        from focus_mv.media import probe
        result['probe'] = probe(media)
        if qc:
            from focus_mv.qc import decode_report
            size = record.get('requested_size', [None, None])
            if size[0] is None:
                size = [plan['timeline']['width'], plan['timeline']['height']]
            a, b = result['timeline_range']
            checks = decode_report(media, out/'technical-qc.json', b-a, size, plan['timeline']['fps'])
            result['qc'] = {'report': str(out/'technical-qc.json'), 'passed': checks['passed']}
        if observation:
            from .observe import observe
            frames = next(s for s in result['probe']['streams'] if s['type'] == 'video')['reported_frames']
            if not frames:
                raise ValueError('No reported frame count for observation; call observe with an explicit range')
            # Bound sample count even for long-form renders.
            from fractions import Fraction
            fps = Fraction(next(s for s in result['probe']['streams'] if s['type'] == 'video')['average_rate'])
            result['observation'] = observe(media, out/'observation', end=frames,
                                            interval=max(2., float(frames/fps)/400))
        result['status'] = 'collected_not_reviewed'
    except Exception as exc:
        result.update(status='failed_partial', error=str(exc))
        raise
    finally:
        save_record(manifest, result)
    return {'collection': str(manifest), **result}


def review(collection, input_path, output):
    collection_path = Path(collection).expanduser().resolve(strict=True)
    artifact = json.loads(collection_path.read_text(encoding='utf-8'))
    if artifact.get('kind') != 'collection' or artifact.get('status') != 'collected_not_reviewed':
        raise ValueError('Use a completed collection record')
    if digest(Path(artifact['media'])) != artifact['sha256']:
        raise ValueError('Rendered file changed since collection')
    note = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if note.get('status') not in ('accepted', 'changes_requested', 'skipped'):
        raise ValueError('Review status must be accepted, changes_requested or skipped')
    if not isinstance(note.get('scope'), str) or not note['scope'].strip():
        raise ValueError('Declare actual review scope or why review was skipped')
    if note['status'] != 'skipped' and not (note.get('observed_artifacts') or note.get('user_feedback')):
        raise ValueError('Declare observed artifacts or explicit user feedback; no automatic aesthetic approval')
    target = Path(output).expanduser().resolve()
    if target.exists():
        raise ValueError('Review output must be new')
    target.parent.mkdir(parents=True, exist_ok=True)
    result = {'kind': 'review', 'collection': str(collection_path), 'render_record': artifact['render_record'],
              'plan_sha256': artifact['plan_sha256'], 'media_sha256': artifact['sha256'],
              'timeline_range': artifact['timeline_range'],
              'declaration': note, 'scope': 'Agent/user-supplied review declaration, not independently verified perception'}
    write_new(target, result)
    return {'review_record': str(target), **result}
