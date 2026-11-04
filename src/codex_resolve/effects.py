"""Composable effects on a newly created Fusion composition only."""
import math
from pathlib import Path


def points(value, frames, name, positive=False):
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError(name+' requires at least two [local_frame,value] keyframes')
    previous = -1
    for pair in value:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError('Invalid keyframe pair')
        frame, scalar = pair
        if isinstance(frame, bool) or not isinstance(frame, int) or not previous < frame < frames:
            raise ValueError('Keyframes must increase inside the output clip')
        if isinstance(scalar, bool) or not isinstance(scalar, (int, float)) or not math.isfinite(scalar):
            raise ValueError('Keyframe values must be finite numbers')
        if positive and scalar <= 0:
            raise ValueError(name+' must be positive')
        previous = frame


def validate(row, fps):
    frames = row['timeline_range'][1]-row['timeline_range'][0]
    retime = row.get('retime')
    if retime:
        from focus_mv.retime import make_plan
        if set(retime)-{'speed', 'method', 'ramp_start', 'ramp_frames'}:
            raise ValueError('Unsupported retime field')
        make_plan(frames=frames, source_start=row['source_range'][0], fps=fps, **retime)
    seen = set()
    for effect in row.get('effects', []):
        kind = effect['type']
        if kind in seen:
            raise ValueError('Use one '+kind+' effect per clip, combining its keyframes')
        seen.add(kind)
        if kind == 'camera':
            if set(effect)-{'type', 'zoom', 'center_x', 'center_y', 'angle'}:
                raise ValueError('Unsupported camera field')
            for key in ('zoom', 'center_x', 'center_y', 'angle'):
                if key in effect:
                    points(effect[key], frames, key, key == 'zoom')
            if not any(k in effect for k in ('zoom', 'center_x', 'center_y', 'angle')):
                raise ValueError('Camera effect requires animation')
        elif kind == 'opacity':
            if set(effect) != {'type', 'keys'}:
                raise ValueError('Opacity effect requires only type and keys')
            points(effect['keys'], frames, 'opacity')
            if any(not 0 <= v <= 1 for _, v in effect['keys']):
                raise ValueError('Opacity keys must be within 0..1')
        else:
            raise ValueError('No adapter for effect: '+str(kind))


def apply(item, row, fps, output):
    if not row.get('effects') and not row.get('retime'):
        return None
    from focus_mv.fusion import animate, persist
    from focus_mv.retime import make_plan, apply as retime_apply
    if item.GetFusionCompCount():
        raise RuntimeError('New clip unexpectedly already has Fusion processing')
    comp = item.AddFusionComp()
    if not comp:
        raise RuntimeError('Cannot create Fusion composition')
    frames = row['timeline_range'][1]-row['timeline_range'][0]
    if row.get('retime'):
        retime_apply(comp, make_plan(frames=frames, source_start=row['source_range'][0],
                                    fps=fps, **row['retime']))
    media_out = comp.FindTool('MediaOut1')
    if not media_out:
        raise RuntimeError('Missing MediaOut1')
    comp.Lock()
    try:
        for effect in row.get('effects', []):
            upstream = media_out.Input.GetConnectedOutput()
            if not upstream:
                raise RuntimeError('Missing source connection')
            if effect['type'] == 'camera':
                tool = comp.AddTool('Transform', 0, 0)
                if not tool:
                    raise RuntimeError('Transform unavailable')
                tool.SetAttrs({'TOOLS_Name': 'CodexResolve_Camera'})
                tool.Input = upstream
                tool.MotionBlur = 0
                tool.Center = comp.XYPath()
                xy = tool.Center.GetConnectedOutput().GetTool()
                for key, node, input_key, default in (
                    ('zoom', tool, 'Size', 1.), ('angle', tool, 'Angle', 0.),
                    ('center_x', xy, 'X', .5), ('center_y', xy, 'Y', .5)):
                    animate(comp, node, input_key, effect.get(key, [[0, default], [frames-1, default]]))
            else:
                bg = comp.AddTool('Background', 0, 1)
                tool = comp.AddTool('Merge', 1, 1)
                if not bg or not tool:
                    raise RuntimeError('Opacity composition nodes unavailable')
                bg.SetAttrs({'TOOLS_Name': 'CodexResolve_Transparent'})
                bg.TopLeftAlpha = 0
                tool.SetAttrs({'TOOLS_Name': 'CodexResolve_Opacity'})
                tool.Background = bg.Output
                tool.Foreground = upstream
                animate(comp, tool, 'Blend', effect['keys'])
            media_out.Input = tool.Output
    finally:
        comp.Unlock()
    # Export/reimport the native composition for persistence, retaining the source binding.
    path = Path(output)
    persist(item, path)
    return str(path)


def prepare_audio(source, row, fps, output):
    """Create a clip-local PCM asset, leaving the user's source unchanged."""
    from fractions import Fraction
    from focus_mv.common import run_ffmpeg
    rate = Fraction(fps)
    a, b = row['source_range']
    duration = float((b-a)/rate)
    filters = ['asetpts=PTS-STARTPTS']
    if row.get('gain_db') is not None:
        filters.append('volume='+str(row['gain_db'])+'dB')
    for key in ('fade_in_frames', 'fade_out_frames'):
        count = row.get(key, 0)
        if count:
            seconds = float(count/rate)
            start = 0 if key == 'fade_in_frames' else duration-seconds
            mode = 'in' if key == 'fade_in_frames' else 'out'
            filters.append(f'afade=t={mode}:st={start:.9f}:d={seconds:.9f}')
    run_ffmpeg(['-v', 'error', '-ss', str(float(a/rate)), '-i', source, '-t', str(duration),
                '-map', '0:a:0', '-vn', '-af', ','.join(filters),
                '-ar', '48000', '-ac', '1' if row.get('layout', 'stereo') == 'mono' else '2',
                '-c:a', 'pcm_s24le', '-n', output])
    from focus_mv.media import probe
    stream = next(s for s in probe(output)['streams'] if s['type'] == 'audio')
    actual = stream['duration_seconds']
    if actual is None or abs(actual-duration) > 2/48000:
        raise ValueError('Prepared audio duration differs; check the source bounds')
    return str(output)
