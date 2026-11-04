"""Source: probe_streams.py, inspect_media.py, stage2_streamcheck.py, cover exporters."""
import json
import math
import re
from pathlib import Path

from .common import fresh_output, make_report, run_ffmpeg, sha256, write_json


def probe(path):
    import av
    streams = []
    with av.open(str(path)) as container:
        for stream in container.streams:
            if stream.type not in ('audio', 'video'):
                continue
            codec = stream.codec_context
            row = {'index': stream.index, 'type': stream.type, 'codec': codec.name,
                   'time_base': str(stream.time_base), 'start_pts': stream.start_time,
                   'duration_seconds': float(stream.duration * stream.time_base) if stream.duration is not None else None,
                   'reported_frames': stream.frames, 'metadata': dict(stream.metadata)}
            if stream.type == 'video':
                row.update(width=codec.width, height=codec.height, average_rate=str(stream.average_rate),
                           pixel_format=codec.format.name if codec.format else None,
                           color_range=str(codec.color_range), colorspace=str(codec.colorspace),
                           color_primaries=str(codec.color_primaries), color_trc=str(codec.color_trc))
            else:
                row.update(sample_rate=codec.sample_rate, layout=codec.layout.name)
            streams.append(row)
    return {'path': str(Path(path).resolve()), 'streams': streams,
            'scope': 'Container metadata; reported frame counts are not decoded counts. Display rotation needs visual review.'}


def packets(path):
    import av
    rows = []
    with av.open(str(path)) as container:
        if not container.streams.video:
            raise ValueError('No video stream')
        stream = container.streams.video[0]
        for packet in container.demux(stream):
            if packet.size:
                rows.append((packet.pts, packet.dts, packet.duration))
        pts = sorted(row[0] for row in rows if row[0] is not None)
        from collections import Counter
        return {'packets': len(rows), 'time_base': str(stream.time_base),
                'first_pts': pts[0] if pts else None, 'last_pts': pts[-1] if pts else None,
                'missing_pts': sum(row[0] is None for row in rows),
                'duplicate_pts': len(pts) - len(set(pts)),
                'sorted_pts_step_histogram': dict(Counter(str(b-a) for a, b in zip(pts, pts[1:]))),
                'duration_tick_histogram': dict(Counter(str(row[2]) for row in rows)),
                'scope': 'Compressed packet timestamps; not decoded integrity or perceptual verification.'}


def probe_report(path, output, with_packets=False):
    fresh_output(output, [path])
    report = make_report('media.probe', [path], {'packets': with_packets})
    report['media'] = probe(path)
    if with_packets:
        report['video_packets'] = packets(path)
    write_json(output, report)
    return report


def frame_sheet(path, output_dir, frame_ids, width=180, columns=6):
    from PIL import Image, ImageDraw, ImageFont
    ids = sorted(set(frame_ids))
    if not ids or any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in ids):
        raise ValueError('Frame indices must be nonnegative integers')
    if len(ids) > 500 or width < 32 or width > 4096 or not 1 <= columns <= 20:
        raise ValueError('Use at most 500 frames, width 32..4096, columns 1..20')
    out = fresh_output(output_dir, [path])
    report = make_report('media.frames', [path], {'frames': ids, 'width': width, 'columns': columns})
    # Directory must be new; no incomplete old cache is silently accepted.
    out.mkdir(parents=True)
    selector = '+'.join('eq(n\\,%d)' % i for i in ids)
    run_ffmpeg(['-v', 'error', '-i', path, '-an', '-vf', f'select={selector},scale={width}:-2',
                '-fps_mode', 'passthrough', '-n', out / 'frame_%04d.png'])
    images = sorted(out.glob('frame_*.png'))
    if len(images) != len(ids):
        raise ValueError(f'Requested {len(ids)} frames, extracted {len(images)}; input too short or decode failed')
    entries = []
    thumbs = []
    for p, frame in zip(images, ids):
        target = out / f'source_frame_{frame:09d}.png'
        p.rename(target)
        with Image.open(target) as im:
            thumbs.append(im.convert('RGB'))
        entries.append({'frame_index': frame, 'file': target.name, 'sha256': sha256(target)})
    h = max(im.height for im in thumbs)
    rows = math.ceil(len(ids) / columns)
    sheet = Image.new('RGB', (columns * width, rows * (h + 26)), '#181818')
    draw = ImageDraw.Draw(sheet)
    for j, (im, frame) in enumerate(zip(thumbs, ids)):
        x, y = j % columns * width, j // columns * (h + 26)
        sheet.paste(im, (x, y))
        draw.text((x + 3, y + h + 3), f'frame {frame}', fill='white')
    sheet.save(out / 'contact_sheet.jpg', quality=92)
    report.update(frames=entries, sheet='contact_sheet.jpg',sheet_sha256=sha256(out/'contact_sheet.jpg'),
                  scope='Zero-based sequential decoded-frame indices; FFmpeg default display rotation. Thumbnails are resized, not native-resolution cover exports.')
    write_json(out / 'manifest.json', report)
    return report


def cover(path, frame, output):
    if frame < 0:
        raise ValueError('Frame must be nonnegative')
    target = fresh_output(output, [path])
    manifest = fresh_output(str(target) + '.json', [path])
    if target.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
        raise ValueError('Cover output must be PNG or JPEG')
    report = make_report('media.cover', [path], {'frame': frame, 'format': target.suffix.lower()})
    target.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(['-v', 'error', '-i', path, '-an', '-vf', f'select=eq(n\\,{frame})',
                '-frames:v', '1', '-fps_mode', 'passthrough', '-n', target])
    if not target.is_file() or not target.stat().st_size:
        raise ValueError('Frame outside input')
    report.update(output=str(target), output_sha256=sha256(target),
                  scope='Native display dimensions; FFmpeg applies rotation metadata. Source frame index is zero-based.')
    write_json(manifest, report)
    return report


def paired_frames(a,b,output_dir,a_indices,offset_frames,width=180):
    from PIL import Image,ImageDraw
    from fractions import Fraction
    ids=sorted(set(a_indices));b_ids=[i-offset_frames for i in ids]
    if not ids or min(ids)<0 or min(b_ids)<0:raise ValueError('Pair indices must fall inside both sources')
    avideo=next(s for s in probe(a)['streams'] if s['type']=='video')
    bvideo=next(s for s in probe(b)['streams'] if s['type']=='video')
    if Fraction(avideo['average_rate'])!=Fraction(bvideo['average_rate']):
        raise ValueError('paired-frames requires matching frame rates; map differing rates explicitly')
    out=fresh_output(output_dir,[a,b])
    report=make_report('media.paired_frames',[a,b],{'a_indices':ids,'offset_frames':offset_frames,'width':width})
    out.mkdir(parents=True)
    aa=frame_sheet(a,out/'A',ids,width,6);bb=frame_sheet(b,out/'B',b_ids,width,6)
    images=[];entries=[]
    for af,bf in zip(aa['frames'],bb['frames']):
        with Image.open(out/'A'/af['file']) as ai,Image.open(out/'B'/bf['file']) as bi:
            images.append((ai.convert('RGB'),bi.convert('RGB')))
        for label,f in [('A',af),('B',bf)]:
            entries.append({'file':label+'/'+f['file'],'sha256':f['sha256']})
    h=max(im.height for pair in images for im in pair);cols=min(6,len(ids));rows=math.ceil(len(ids)/cols)
    sheet=Image.new('RGB',(cols*width,rows*(2*h+52)),'#181818');draw=ImageDraw.Draw(sheet)
    for j,((ai,bi),af,bf) in enumerate(zip(images,ids,b_ids)):
        x=j%cols*width;y=j//cols*(2*h+52)
        sheet.paste(ai,(x,y));draw.text((x+2,y+h+3),f'A frame {af}',fill='white')
        sheet.paste(bi,(x,y+h+26));draw.text((x+2,y+2*h+29),f'B frame {bf}',fill='white')
    sheet.save(out/'paired_sheet.jpg',quality=92)
    report.update(frames=entries,sheet='paired_sheet.jpg',sheet_sha256=sha256(out/'paired_sheet.jpg'),
                  mapping='B_frame = A_frame - offset_frames',pairs=list(zip(ids,b_ids)),
                  scope='Same-rate integer source-frame comparison. Offset is a supplied candidate, not proof of correct visual sync.')
    write_json(out/'manifest.json',report)
    return report
