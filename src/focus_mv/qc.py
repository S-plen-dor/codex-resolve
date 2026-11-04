"""Source: verify_full.py, finish_delivery.py, V5 packet-copy verification."""
import hashlib
import re

import numpy as np
from scipy import signal

from .common import finite, fresh_output, make_report, rate, run_ffmpeg, write_json
from .media import probe
from .sync import read_audio


def decode_report(path, output, expected_frames=None, expected_size=None, expected_fps=None):
    fresh_output(output,[path])
    report=make_report('qc.decode',[path],{'expected_frames':expected_frames,'expected_size':expected_size,'expected_fps':expected_fps})
    info=probe(path)
    videos=[s for s in info['streams'] if s['type']=='video']
    if not videos:raise ValueError('No video stream')
    video=videos[0]
    result=run_ffmpeg(['-v','info','-xerror','-err_detect','explode','-i',path,
                      '-map','0:v:0','-map','0:a?','-vf','blackdetect=d=0.02:pix_th=0.02:pic_th=0.98',
                      '-progress','pipe:1','-nostats','-f','null','-'])
    progress=result.stdout.decode(errors='replace')
    counts=re.findall(r'^frame=(\d+)',progress,re.M)
    if not counts:raise ValueError('Decoder did not report frame count')
    decoded=int(counts[-1])
    black=[{'start':float(a),'end':float(b),'duration':float(c)} for a,b,c in re.findall(
        r'black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)',result.stderr.decode(errors='replace'))]
    checks={'full_video_audio_decode':True}
    if expected_frames is not None:checks['frames']=decoded==expected_frames
    if expected_size is not None:checks['dimensions']=[video['width'],video['height']]==list(expected_size)
    if expected_fps is not None:checks['fps']=rate(video['average_rate'])==rate(expected_fps)
    report.update(passed=all(checks.values()),checks=checks,decoded_frames=decoded,media=info,black_candidates=black,
                  scope='Full FFmpeg decode of first video and all audio streams. Black intervals are candidates, including intentional fades; not perceptual, lip-sync, framing or optical-flow acceptance.')
    write_json(output,report)
    return report


def audio_signature(path):
    import av
    digest=hashlib.sha256(); payload=hashlib.sha256(); count=0
    with av.open(str(path)) as container:
        if not container.streams.audio:raise ValueError('No audio stream')
        stream=container.streams.audio[0]
        meta={'codec':stream.codec_context.name,'time_base':str(stream.time_base),
              'extradata_sha256':hashlib.sha256(stream.codec_context.extradata or b'').hexdigest(),
              'sample_rate':stream.codec_context.sample_rate,'layout':stream.codec_context.layout.name}
        for packet in container.demux(stream):
            if not packet.size:continue
            data=bytes(packet)
            payload.update(len(data).to_bytes(8,'big'));payload.update(data)
            stamp=repr((packet.pts,packet.dts,packet.duration,packet.size)).encode()
            digest.update(len(stamp).to_bytes(8,'big'));digest.update(stamp);digest.update(data);count+=1
    return {**meta,'packets':count,'payload_sha256':payload.hexdigest(),'packets_and_timestamps_sha256':digest.hexdigest()}


def compare_audio(a,b,output,mode='waveform',max_lag=.5,min_corr=.98,max_offset_ms=2.):
    fresh_output(output,[a,b])
    max_lag=finite(max_lag,'max-lag');max_offset_ms=finite(max_offset_ms,'max-offset-ms')
    if max_lag<0 or max_offset_ms<0 or not 0<min_corr<=1:raise ValueError('Invalid audio comparison thresholds')
    report=make_report('qc.audio',[a,b],{'mode':mode,'max_lag':max_lag,'min_corr':min_corr,'max_offset_ms':max_offset_ms})
    if mode=='packets':
        sa,sb=audio_signature(a),audio_signature(b)
        report.update(passed=sa==sb,a=sa,b=sb,scope='First audio stream: codec metadata, compressed packet payloads and timestamps. Re-encoded audio may legitimately differ.')
    elif mode=='waveform':
        x,y=read_audio(a),read_audio(b)
        if min(np.std(x),np.std(y))<1e-7:raise ValueError('Silent audio cannot establish alignment')
        c=signal.correlate(y-y.mean(),x-x.mean(),method='fft')
        lags=signal.correlation_lags(len(y),len(x))
        mask=np.abs(lags)<=round(max_lag*16000)
        lag=int(lags[mask][np.argmax(c[mask])])
        # positive lag means B is delayed relative to A
        start_a=max(0,-lag);start_b=max(0,lag);n=min(len(x)-start_a,len(y)-start_b)
        if n<1600:raise ValueError('Less than 100 ms overlapping audio')
        aa=x[start_a:start_a+n];bb=y[start_b:start_b+n]
        cor=float(np.corrcoef(aa,bb)[0,1]);gain=float(20*np.log10(np.sqrt(np.mean(bb**2))/np.sqrt(np.mean(aa**2))))
        report.update(passed=cor>=min_corr and abs(lag/16)<=max_offset_ms,
                      lag_samples=lag,lag_ms=lag/16,correlation=cor,gain_difference_db=gain,
                      duration_a=len(x)/16000,duration_b=len(y)/16000,overlap_seconds=n/16000,
                      duration_difference_seconds=(len(y)-len(x))/16000,
                      scope='16 kHz mono waveform alignment; positive lag means B is delayed. Does not prove visual sync or unchanged stereo mix. Inspect duration difference separately.')
    else:raise ValueError('Unknown comparison mode')
    write_json(output,report)
    return report
