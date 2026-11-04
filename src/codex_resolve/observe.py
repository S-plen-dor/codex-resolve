"""Build an on-demand visual evidence pack, without assigning aesthetic scores."""
import math
from fractions import Fraction
from pathlib import Path

from focus_mv.common import fresh_output, run_ffmpeg, write_json
from focus_mv.media import frame_sheet, probe


def observe(source, output, start=0, end=None, interval=5.0, width=360, clip=False):
    source = Path(source).expanduser().resolve(strict=True)
    out = fresh_output(output, [source])
    media = probe(source)
    video = next((s for s in media['streams'] if s['type'] == 'video'), None)
    if video is None:
        raise ValueError('Observation packs require a video stream')
    fps = Fraction(video['average_rate'])
    if fps <= 0 or not math.isfinite(interval) or interval <= 0 or start < 0:
        raise ValueError('Use positive rate/interval and a nonnegative start frame')
    if end is None:
        end = video['reported_frames']
        if not end:
            raise ValueError('No reported frame count; provide --end explicitly')
    if end <= start:
        raise ValueError('Use an exclusive end frame greater than start')
    step = max(1, round(interval * fps))
    frames = list(range(start, end, step))
    if len(frames) > 500:
        raise ValueError('More than 500 samples; increase interval or split the range')
    if clip and (end-start)/fps > 60:
        raise ValueError('Optional continuous clip is limited to 60 seconds; choose a candidate range')
    out.mkdir(parents=True)
    # A failed extraction leaves an incomplete directory, never a successful manifest.
    sheet = frame_sheet(source, out/'frames', frames, width=width, columns=6)
    rows = [{'frame': entry['frame_index'], 'seconds': float(entry['frame_index']/fps),
             'image': 'frames/' + entry['file']} for entry in sheet['frames']]
    if clip:
        run_ffmpeg(['-v', 'error', '-ss', str(float(start/fps)), '-i', source,
                    '-t', str(float((end-start)/fps)), '-map', '0:v:0', '-map', '0:a:0?',
                    '-vf', 'scale=720:-2', '-c:v', 'libx264', '-crf', '23',
                    '-c:a', 'aac', '-movflags', '+faststart', '-n', out/'review.mp4'])
    report = {'schema_version': 1, 'source': media, 'fps': str(fps),
              'source_sha256': sheet['inputs_sha256'][0], 'range': [start, end],
              'samples': rows, 'contact_sheet': 'frames/contact_sheet.jpg',
              'clip': 'review.mp4' if clip else None,
              'scope': 'Frame-index samples with nominal-rate seconds; clip seeks are time-based. '
                       'Not a VFR frame-time mapping, action recognition or proof of continuous viewing.'}
    lines = ['# Observation pack', '', 'Inspect these actual images before making creative claims.', '',
             '![Overview](frames/contact_sheet.jpg)', '']
    if clip:
        lines.extend(['[Continuous candidate clip with source audio](review.mp4)', ''])
    lines.extend(f"- Frame {r['frame']} / nominal {r['seconds']:.3f}s: [{Path(r['image']).name}]({r['image']})" for r in rows)
    (out/'INDEX.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    write_json(out/'observation.json', report)
    return {'observation': str(out/'observation.json'), 'index': str(out/'INDEX.md'),
            'sample_count': len(rows), 'scope': report['scope']}
