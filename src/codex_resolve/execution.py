"""Explicit Resolve mutations. Imports are inert; no implicit project switching."""
import json
import os
import hashlib
from fractions import Fraction
from pathlib import Path

from .plan import executable, load_plan
from .project import write_new
from .resolve import connect


def require(value, message):
    if not value:
        raise RuntimeError(message)
    return value


def target(name, uid=None, idle=True):
    resolve = connect()
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject()
    require(project and project.GetName() == name, 'Current project does not match --project')
    if uid:
        require(project.GetUniqueId() == uid, 'Project identity differs from operation record')
    if idle:
        require(not project.IsRenderingInProgress(), 'Project is currently rendering')
    return resolve, manager, project


def save_record(path, record):
    # Only replace the journal owned by this operation.
    temporary = path.with_suffix('.tmp')
    with temporary.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    os.replace(temporary, path)


def setting(timeline, key, value):
    modern = getattr(timeline, 'SetSettings', None)
    if callable(modern):
        require(modern({key: str(value)}), 'Timeline rejected '+key)
    else:
        require(timeline.SetSetting(key, str(value)), 'Timeline rejected '+key)


def read_settings(timeline):
    modern = getattr(timeline, 'GetSettings', None)
    return modern() if callable(modern) else timeline.GetSetting()


def timeline_fingerprint(timeline):
    """Detect basic manual edits before rendering; not a Fusion/color graph audit."""
    rows = []
    for kind in ('video', 'audio'):
        for index in range(1, timeline.GetTrackCount(kind)+1):
            rows.append({'track': [kind, index], 'enabled': timeline.GetIsTrackEnabled(kind, index)})
            for item in timeline.GetItemListInTrack(kind, index) or []:
                source = item.GetMediaPoolItem()
                rows.append({'id': item.GetUniqueId(), 'track': [kind, index],
                             'start': item.GetStart(), 'duration': item.GetDuration(),
                             'source_start': item.GetSourceStartFrame(),
                             'source': source.GetUniqueId() if source else None})
    spec = {'settings': read_settings(timeline), 'items': rows}
    return hashlib.sha256(json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()


def apply(path, project_name, timeline_name, output, save_current=False):
    if not save_current:
        raise ValueError('Applying requires --save-current: it saves and exports the current project before editing')
    plan = executable(load_plan(path))
    # Complete media preflight before connecting or mutating Resolve.
    from focus_mv.media import probe, packets
    for source in plan['sources'].values():
        info = probe(source['absolute_path'])
        video = next((s for s in info['streams'] if s['type'] == 'video'), None)
        require(video is not None, 'First executor requires video-backed sources, including audio clips')
        require(Fraction(video['average_rate']) == Fraction(source['fps']), 'Declared source rate differs from media')
        timing = packets(source['absolute_path'])
        require(not timing['missing_pts'] and not timing['duplicate_pts'] and
                len(timing['sorted_pts_step_histogram']) == 1, 'VFR or irregular timestamps need another adapter')
        for row in plan['data']['shots'] + plan['data'].get('audio', []):
            if row['source_id'] == source['id']:
                if video['reported_frames']:
                    require(row['source_range'][1] <= video['reported_frames'], 'Source range exceeds reported frames')
                if row in plan['data'].get('audio', []):
                    require(any(s['type'] == 'audio' for s in info['streams']), 'Requested audio source has no audio')
    out = Path(output).expanduser().resolve()
    if out.exists():
        raise ValueError('Operation directory already exists; inspect its journal before retrying')
    if not timeline_name.strip():
        raise ValueError('Provide a new timeline name')
    _, manager, project = target(project_name)
    for index in range(1, project.GetTimelineCount()+1):
        require(project.GetTimelineByIndex(index).GetName() != timeline_name, 'Timeline name already exists')
    previous = project.GetCurrentTimeline()
    out.mkdir(parents=True)
    journal = out/'operation.json'
    record = {'schema_version': 1, 'kind': 'apply', 'status': 'started',
              'project': project_name, 'project_id': project.GetUniqueId(),
              'timeline': timeline_name, 'plan_sha256': plan['sha256'],
              'original_plan': plan['path'], 'project_root': plan['root'], 'clips': []}
    write_new(out/'plan.json', plan['data'])
    save_record(journal, record)
    try:
        require(manager.SaveProject(), 'Cannot save current project')
        backup = out/'before.drp'
        require(manager.ExportProject(project_name, str(backup)), 'Project backup failed')
        require(backup.is_file() and backup.stat().st_size, 'Backup file missing or empty')
        record['backup'] = str(backup)
        save_record(journal, record)
        pool = project.GetMediaPool()
        timeline = require(pool.CreateEmptyTimeline(timeline_name), 'Cannot create work timeline')
        record['timeline_id'] = timeline.GetUniqueId()
        save_record(journal, record)
        require(project.SetCurrentTimeline(timeline), 'Cannot activate work timeline')
        settings = plan['data']['timeline']
        setting(timeline, 'useCustomSettings', '1')
        setting(timeline, 'timelineResolutionWidth', settings['width'])
        setting(timeline, 'timelineResolutionHeight', settings['height'])
        # Resolve uses decimal display-rate strings at this boundary.
        rate = Fraction(settings['fps'])
        setting(timeline, 'timelineFrameRate', f'{float(rate):.3f}'.rstrip('0').rstrip('.'))
        actual = read_settings(timeline)
        require(int(actual['timelineResolutionWidth']) == settings['width'] and
                int(actual['timelineResolutionHeight']) == settings['height'], 'Timeline dimensions differ')
        require(abs(float(str(actual['timelineFrameRate']).split()[0])-float(rate)) < .001,
                'Timeline frame rate differs')
        base = timeline.GetStartFrame()
        media = {}
        for key, source in plan['sources'].items():
            imported = pool.ImportMedia([source['absolute_path']])
            require(imported and len(imported) == 1, 'Cannot uniquely import '+key)
            media[key] = imported[0]
        audio = plan['data'].get('audio', [])
        # Empty timelines may contain default mono tracks. Replace only empty defaults in this new timeline.
        for index in range(timeline.GetTrackCount('audio'), 0, -1):
            require(not timeline.GetItemListInTrack('audio', index), 'New timeline has unexpected audio')
            require(timeline.DeleteTrack('audio', index), 'Cannot remove empty default track')
        video_count = max(row.get('track', 1) for row in plan['data']['shots'])
        while timeline.GetTrackCount('video') < video_count:
            require(timeline.AddTrack('video'), 'Cannot create video track')
        layouts = {r.get('track', 1): r.get('layout', 'stereo') for r in audio}
        for index in range(1, max(layouts, default=0)+1):
            layout = layouts.get(index, 'stereo')
            require(timeline.AddTrack('audio', layout), 'Cannot create audio track')
            require(timeline.GetTrackSubType('audio', index).lower() == layout, 'Audio track layout differs')
        for kind, rows in ((1, plan['data']['shots']), (2, audio)):
            for row in sorted(rows, key=lambda r: (r.get('track', 1), r['timeline_range'][0])):
                a, b = row['source_range']
                c, d = row['timeline_range']
                items = pool.AppendToTimeline([{'mediaPoolItem': media[row['source_id']],
                    'startFrame': a, 'endFrame': b-1, 'recordFrame': base+c,
                    'trackIndex': row.get('track', 1), 'mediaType': kind}])
                require(items and len(items) == 1, 'Cannot insert '+row['id'])
                item = items[0]
                # Record the mutation before validating it, retaining evidence on failure.
                result = {'id': row['id'], 'item_id': item.GetUniqueId(),
                          'start': item.GetStart(), 'duration': item.GetDuration()}
                record['clips'].append(result)
                save_record(journal, record)
                require(abs(result['start']-(base+c)) < .001 and abs(result['duration']-(d-c)) < .001,
                        'Actual insertion range differs: '+row['id'])
                require(item.GetMediaPoolItem().GetUniqueId() == media[row['source_id']].GetUniqueId(),
                        'Source binding differs: '+row['id'])
                require(item.GetSourceStartFrame() == a, 'Source offset differs: '+row['id'])
                props = row.get('properties', {})
                if props:
                    modern = getattr(item, 'SetProperties', None)
                    require(modern(props) if callable(modern) else item.SetProperty(props), 'Cannot set clip properties')
                    read = getattr(item, 'GetProperties', None)
                    values = read() if callable(read) else item.GetProperty()
                    require(all(abs(float(values[k])-v) < .001 for k, v in props.items()), 'Clip properties differ')
        require(manager.SaveProject(), 'Cannot save work timeline')
        record['timeline_fingerprint'] = timeline_fingerprint(timeline)
        record['duration_frames'] = plan['duration_frames']
        record['status'] = 'built_not_reviewed'
        record['scope'] = 'Readback checks only; no reopen, rendered or perceptual validation'
    except Exception as exc:
        record.update(status='failed_partial', error=str(exc))
        raise
    finally:
        if previous:
            record['previous_timeline_restored'] = bool(project.SetCurrentTimeline(previous))
        save_record(journal, record)
    return {'operation': str(journal), **record}


def render(operation, output, preset, start=False):
    record = json.loads(Path(operation).read_text(encoding='utf-8'))
    require(record.get('kind') == 'apply' and record.get('status') == 'built_not_reviewed', 'Use a completed apply record')
    _, _, project = target(record['project'], record['project_id'])
    timeline = next((project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount()+1)
                     if project.GetTimelineByIndex(i).GetUniqueId() == record['timeline_id']), None)
    require(timeline, 'Work timeline no longer exists')
    require(timeline_fingerprint(timeline) == record['timeline_fingerprint'],
            'Timeline changed after build; inspect changes before creating a new operation')
    require(preset in project.GetRenderPresetList(), 'Named render preset is unavailable')
    out = Path(output).expanduser().resolve()
    if out.exists():
        raise ValueError('Render directory must be new')
    out.mkdir(parents=True)
    journal = out/'render.json'
    result = {'kind': 'render', 'project': record['project'], 'project_id': record['project_id'],
              'timeline_id': record['timeline_id'], 'preset': preset, 'status': 'preparing',
              'output_directory': str(out), 'operation': str(Path(operation).resolve())}
    previous = project.GetCurrentTimeline()
    save_record(journal, result)
    try:
        require(project.SetCurrentTimeline(timeline), 'Cannot select work timeline')
        require(project.LoadRenderPreset(preset), 'Cannot load render preset')
        require(project.SetCurrentRenderMode(1), 'Cannot select single-clip render')
        # Use explicit inclusive render bounds. No quality/codec claims beyond the selected preset.
        require(project.SetRenderSettings({'TargetDir': str(out), 'CustomName': 'preview',
                    'MarkIn': timeline.GetStartFrame(),
                    'MarkOut': timeline.GetStartFrame()+record['duration_frames']-1,
                    'SelectAllFrames': False, 'ExportVideo': True}), 'Render settings rejected')
        job = require(project.AddRenderJob(), 'Cannot queue render')
        result.update(job_id=job, status='queued')
        save_record(journal, result)
        if start:
            require(project.StartRendering([job]), 'Cannot start render; queued job retained')
            result['status'] = 'submitted'
    except Exception as exc:
        result.update(status='failed', error=str(exc))
        raise
    finally:
        # Do not switch timelines while an asynchronous render is running.
        if previous and not project.IsRenderingInProgress():
            result['previous_timeline_restored'] = bool(project.SetCurrentTimeline(previous))
        save_record(journal, result)
    return {'record': str(journal), **result}


def render_status(path):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    require(record.get('kind') == 'render' and record.get('job_id'), 'Record has no queued job')
    _, _, project = target(record['project'], record['project_id'], idle=False)
    return {'job_id': record['job_id'], 'status': project.GetRenderJobStatus(record['job_id']),
            'output_directory': record['output_directory'],
            'scope': 'Render job status only; output files and perceptual quality are not verified'}
