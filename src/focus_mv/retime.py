"""Source: create_time_plan.py integral smoothstep and build_interpolation_tests.py.

Planning is pure Python; apply() is an explicit Resolve object operation.
"""
import math

from .common import finite,fresh_output,make_report,rate,write_json


def evaluate(rows,frame):
    if frame<=rows[0]['f']:return rows[0]['v']
    for a,b in zip(rows,rows[1:]):
        if frame<=b['f']:
            t=(frame-a['f'])/(b['f']-a['f']);q=1-t
            return q**3*a['v']+3*q*q*t*(a['v']+a['rh'][1])+3*q*t*t*(b['v']+b['lh'][1])+t**3*b['v']
    return rows[-1]['v']


def make_plan(frames,speed=.8,method='speedwarp',ramp_start=0,ramp_frames=0,source_start=0,fps='60000/1001'):
    if isinstance(frames,bool) or not isinstance(frames,int) or not 2<=frames<=36000:raise ValueError('frames must be an integer 2..36000')
    if isinstance(source_start,bool) or not isinstance(source_start,int) or source_start<0:raise ValueError('source-start must be a nonnegative integer')
    speed=finite(speed,'speed');fps=rate(fps)
    if not 0<speed<=1:raise ValueError('Only 0 < speed <= 1; no accelerated catch-up')
    if method not in ('speedwarp','flow'):raise ValueError('method must be speedwarp or flow')
    if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in [ramp_start,ramp_frames]):raise ValueError('Ramp positions must be nonnegative integers')
    if ramp_frames==0 and ramp_start!=0:raise ValueError('Constant speed uses ramp-start=0; provide ramp-frames for a normal-speed lead-in')
    if ramp_frames and ramp_start+ramp_frames>=frames:raise ValueError('Ramp must fit within output frames')
    def delay(f):
        if not ramp_frames:return (1-speed)*f,1-speed
        if f<=ramp_start:return 0.,0.
        if f>=ramp_start+ramp_frames:return (1-speed)*(f-ramp_start-ramp_frames/2),1-speed
        u=(f-ramp_start)/ramp_frames
        return (1-speed)*ramp_frames*(u**3-.5*u**4),(1-speed)*(3*u*u-2*u*u*u)
    fs=sorted(set([0,frames-1]+([ramp_start,ramp_start+ramp_frames]+list(range(ramp_start,ramp_start+ramp_frames,3)) if ramp_frames else [])))
    curve=[]
    for j,f in enumerate(fs):
        v,m=delay(f)
        curve.append({'f':f,'v':v,'lh':[-(f-fs[j-1])/3,-m*(f-fs[j-1])/3] if j else None,
                      'rh':[(fs[j+1]-f)/3,m*(fs[j+1]-f)/3] if j+1<len(fs) else None})
    source_curve=[]
    for row in curve:
        source_curve.append({'f':row['f'],'v':row['f']-row['v'],
             'lh':[row['lh'][0],row['lh'][0]-row['lh'][1]] if row['lh'] else None,
             'rh':[row['rh'][0],row['rh'][0]-row['rh'][1]] if row['rh'] else None})
    mapping=[f-evaluate(curve,f) for f in range(frames)]
    if min(mapping)<-1e-8 or max(mapping)>frames-1+1e-8 or any(b<a for a,b in zip(mapping,mapping[1:])):raise ValueError('Invalid or backward source mapping')
    return {'schema_version':1,'frames':frames,'speed':speed,'method':method,'mode':'ModeFaster' if method=='speedwarp' else 'Advanced',
            'ramp_start':ramp_start,'ramp_frames':ramp_frames,'source_start':source_start,'fps':str(fps),
            'delay_curve':curve,'source_time_curve':source_curve,'source_local_by_output_frame':mapping,
            'source_absolute_exit_frame':source_start+mapping[-1],'exit_delay_frames':frames-1-mapping[-1],
            'audio_policy':'Do not retime the continuous master audio',
            'next_shot_policy':'Choose next source at its own master-sync position; do not carry delay forward or accelerate to catch up',
            'scope':'Video-local timing plan. No automatic next-shot selection, timeline edits or perceptual acceptance.'}


def plan_report(output,**kwargs):
    fresh_output(output);plan=make_plan(**kwargs)
    parameters={k:plan[k] for k in ['frames','speed','method','ramp_start','ramp_frames','source_start','fps']}
    report=make_report('retime.plan',[],parameters);report.update(passed=True,plan=plan)
    write_json(output,report);return report


def spline(comp,tool,key,rows):
    tool[key]=comp.BezierSpline();sp=tool[key].GetConnectedOutput().GetTool();keys={}
    for r in rows:
        value={1:r['v']}
        if r['lh'] is not None:value['LH']={1:r['lh'][0],2:r['lh'][1]}
        if r['rh'] is not None:value['RH']={1:r['rh'][0],2:r['rh'][1]}
        keys[r['f']]=value
    sp.SetKeyFrames(keys,True)


def apply(comp,plan):
    # Regenerate from validated scalar inputs; never trust arbitrary serialized node/curve data.
    params={k:plan[k] for k in ['frames','speed','method','ramp_start','ramp_frames','source_start','fps']}
    checked=make_plan(**params)
    for key in ['delay_curve','source_time_curve','source_local_by_output_frame']:
        if plan[key]!=checked[key]:raise ValueError('Plan mapping differs from validated parameters')
    mi=comp.FindTool('MediaIn1');mo=comp.FindTool('MediaOut1')
    if not mi or not mo:raise ValueError('Missing MediaIn1/MediaOut1')
    connected=mo.Input.GetConnectedOutput()
    if not connected or connected.GetTool().GetAttrs().get('TOOLS_Name')!=mi.GetAttrs().get('TOOLS_Name'):
        raise ValueError('Retime helper requires an unprocessed composition')
    props=mi.GetData('MediaProps')
    if not props or -props['MEDIA_START_FRAME']!=plan['source_start']:raise ValueError('Plan source start does not match clip binding')
    if comp.FindTool('FocusMV_Retime'):raise ValueError('Retime node already present')
    comp.Lock()
    try:
        if plan['method']=='flow':
            flow=comp.AddTool('Dimension.OpticalFlow',0,0)
            if not flow:raise RuntimeError('OpticalFlow node unavailable')
            flow.SetAttrs({'TOOLS_Name':'FocusMV_OpticalFlow'});flow.Input=mi.Output;flow.Method='Advanced'
            ret=comp.AddTool('TimeStretcher',1,0)
            if not ret:raise RuntimeError('TimeStretcher unavailable')
            ret.Input=flow.Output;ret.InterpolateBetweenFrames=2;ret.ClampEdges=1
            spline(comp,ret,'SourceTime',plan['source_time_curve'])
        else:
            ret=comp.AddTool('SpeedWarp',0,0)
            if not ret:raise RuntimeError('SpeedWarp node unavailable')
            ret.Input=mi.Output;ret.Speed=1.;ret.Mode='ModeFaster'
            spline(comp,ret,'Delay',plan['delay_curve'])
        ret.SetAttrs({'TOOLS_Name':'FocusMV_Retime'});mo.Input=ret.Output
    finally:comp.Unlock()
    return ret
