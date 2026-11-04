"""Source: inspect_interpolation.py and verify_cache_match.py; measured candidates only."""
import json
from pathlib import Path

import cv2
import numpy as np

from .common import fresh_output,make_report,write_json,rate
from .retime import make_plan


def read_frame(cap,index,size):
    cap.set(cv2.CAP_PROP_POS_FRAMES,index);ok,bgr=cap.read()
    if not ok:raise ValueError('Cannot decode requested frame '+str(index))
    return cv2.resize(bgr,size,interpolation=cv2.INTER_AREA)


def check_mapping(source,render,plan_file,output,render_start=0,probes=12,search=3,tolerance=1.5):
    fresh_output(output,[source,render,plan_file])
    data=json.loads(Path(plan_file).read_text(encoding='utf-8-sig'));p=data['plan'] if 'plan' in data else data
    params={k:p[k] for k in ['frames','speed','method','ramp_start','ramp_frames','source_start','fps']};checked=make_plan(**params)
    if p['source_local_by_output_frame']!=checked['source_local_by_output_frame']:raise ValueError('Invalid plan mapping')
    if not 2<=probes<=100 or not 1<=search<=10 or render_start<0 or tolerance<0:raise ValueError('Invalid QC sampling parameters')
    report=make_report('retime.check',[source,render,plan_file],{'render_start':render_start,'probes':probes,'search':search,'tolerance_frames':tolerance})
    a=cv2.VideoCapture(str(source));b=cv2.VideoCapture(str(render));rows=[]
    try:
        for cap in [a,b]:
            if abs(cap.get(cv2.CAP_PROP_FPS)-float(rate(p['fps'])))>1e-3:raise ValueError('Frame rate mismatch; this check requires source and render to match plan')
        for f in sorted(set(int(x) for x in np.linspace(0,p['frames']-1,probes))):
            expected=p['source_start']+p['source_local_by_output_frame'][f]
            target=cv2.cvtColor(read_frame(b,render_start+f,(180,320)),cv2.COLOR_BGR2GRAY).astype(float)
            scores=[]
            for index in range(max(0,int(np.floor(expected))-search),int(np.ceil(expected))+search+1):
                raw=cv2.cvtColor(read_frame(a,index,(180,320)),cv2.COLOR_BGR2GRAY).astype(float)
                scores.append({'source_frame':index,'mean_abs_error':float(np.mean(abs(raw-target)))})
            best=min(scores,key=lambda r:r['mean_abs_error']);delta=abs(best['source_frame']-expected)
            rows.append({'output_frame':render_start+f,'expected_source_frame':expected,'best_integer_neighbor':best['source_frame'],
                         'source_error_frames':delta,'scores':scores,'within_tolerance':delta<=tolerance})
    finally:a.release();b.release()
    report.update(passed=all(r['within_tolerance'] for r in rows),samples=rows,
       scope='Nearest source-neighbor sample check, requiring identical geometry. Interpolated moving edges, repeated/static frames or grading may bias matches. Does not prove smoothness or absence of optical-flow deformation.')
    write_json(output,report);return report


def cache_match(cache,render,output,frames,render_start=0,cache_start=0,min_corr=.995,max_mae=3.):
    fresh_output(output,[cache,render])
    if frames<1 or min(render_start,cache_start)<0 or not 0<min_corr<=1 or max_mae<0:raise ValueError('Invalid cache comparison parameters')
    report=make_report('retime.cache_match',[cache,render],{'frames':frames,'render_start':render_start,'cache_start':cache_start,
                                'min_corr':min_corr,'max_mae':max_mae,'comparison_size':[270,480]})
    a=cv2.VideoCapture(str(cache));b=cv2.VideoCapture(str(render));rows=[]
    try:
        if abs(a.get(cv2.CAP_PROP_FPS)-b.get(cv2.CAP_PROP_FPS))>1e-3:raise ValueError('Cache/render frame rates differ')
        a.set(cv2.CAP_PROP_POS_FRAMES,cache_start);b.set(cv2.CAP_PROP_POS_FRAMES,render_start)
        for i in range(frames):
            ok,x=a.read();ok2,y=b.read()
            if not ok or not ok2:raise ValueError('Cache/render shorter than requested comparison')
            x=cv2.resize(x,(270,480)).astype(float);y=cv2.resize(y,(270,480)).astype(float)
            mae=float(np.mean(abs(x-y)))
            # Constant frames have undefined correlation; don't hide unequal flat images.
            cor=float(np.corrcoef(x.ravel(),y.ravel())[0,1]) if min(x.std(),y.std())>1e-8 else (1. if np.array_equal(x,y) else 0.)
            rows.append({'local_frame':i,'mae':mae,'correlation':cor})
    finally:a.release();b.release()
    report.update(passed=all(r['mae']<=max_mae and r['correlation']>=min_corr for r in rows),frames_compared=frames,
                  maximum_mae=max(r['mae'] for r in rows),minimum_correlation=min(r['correlation'] for r in rows),
                  failed_frames=[r for r in rows if r['mae']>max_mae or r['correlation']<min_corr],
                  scope='All requested frames compared at 270x480. Supports cache/render match, not native-resolution pixel identity or creative acceptance.')
    write_json(output,report);return report
