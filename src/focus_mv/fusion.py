"""No Resolve connection on import. Source: existing animate/ease/persist implementations.

Call inside a Resolve scripting session only, passing explicit objects.
"""
import math
from pathlib import Path


def _check_points(points):
    points=list(points)
    if len(points)<2:raise ValueError('At least two keyframes required')
    previous=-1
    for f,v in points:
        if isinstance(f,bool) or not isinstance(f,int) or f<0 or f<=previous:
            raise ValueError('Frames must be increasing nonnegative integers')
        if not math.isfinite(float(v)):raise ValueError('Keyframe value must be finite')
        previous=f
    return points


def ease_rows(points):
    points=_check_points(points)
    return [{'f':f,'v':v,'lh':[-(f-points[j-1][0])/3,0] if j else None,
             'rh':[(points[j+1][0]-f)/3,0] if j+1<len(points) else None}
            for j,(f,v) in enumerate(points)]


def animate(comp,tool,key,points):
    rows=ease_rows(points)
    tool[key]=comp.BezierSpline()
    spline=tool[key].GetConnectedOutput().GetTool()
    keys={}
    for row in rows:
        value={1:row['v']}
        if row['lh'] is not None:value['LH']={1:row['lh'][0],2:row['lh'][1]}
        if row['rh'] is not None:value['RH']={1:row['rh'][0],2:row['rh'][1]}
        keys[row['f']]=value
    spline.SetKeyFrames(keys,True)
    return rows


def require_target(project,project_name,timeline_name):
    if not project or project.GetName()!=project_name:raise ValueError('Wrong Resolve project')
    if project.IsRenderingInProgress():raise ValueError('Project is rendering')
    timeline=project.GetCurrentTimeline()
    if not timeline or timeline.GetName()!=timeline_name:raise ValueError('Wrong timeline')
    return timeline


def camera(comp,*,zoom,center_x=((0,.5),(59,.5)),center_y=((0,.5),(59,.5)),angle=((0,0.),(59,0.))):
    # Validate before creating nodes; coordinates are Fusion Center, not source-space crop centers.
    for points in [zoom,center_x,center_y,angle]:_check_points(points)
    if any(v<=0 for _,v in zoom):raise ValueError('Zoom must be positive')
    media_in=comp.FindTool('MediaIn1');media_out=comp.FindTool('MediaOut1')
    if not media_in or not media_out:raise ValueError('Missing MediaIn1/MediaOut1')
    if comp.FindTool('FocusMV_Camera'):raise ValueError('Camera already exists')
    connected=media_out.Input.GetConnectedOutput()
    source_name=connected.GetTool().GetAttrs().get('TOOLS_Name') if connected else None
    input_name=media_in.GetAttrs().get('TOOLS_Name')
    if source_name!=input_name:
        raise ValueError(f'Camera helper requires an unprocessed composition; upstream={source_name!r}, MediaIn={input_name!r}')
    comp.Lock()
    try:
        transform=comp.AddTool('Transform',0,0)
        transform.SetAttrs({'TOOLS_Name':'FocusMV_Camera'})
        transform.Input=media_in.Output;transform.MotionBlur=0
        transform.Center=comp.XYPath()
        xy=transform.Center.GetConnectedOutput().GetTool()
        animate(comp,transform,'Size',zoom)
        animate(comp,transform,'Angle',angle)
        animate(comp,xy,'X',center_x)
        animate(comp,xy,'Y',center_y)
        media_out.Input=transform.Output
    finally:comp.Unlock()
    return transform


def persist(item,path):
    path=Path(path).resolve()
    if path.suffix.lower()!='.comp' or path.exists():raise ValueError('Use a new .comp output path')
    if item.GetFusionCompCount()!=1:raise ValueError('Expected exactly one Fusion composition')
    path.parent.mkdir(parents=True,exist_ok=True)
    if not item.ExportFusionComp(str(path),1):raise RuntimeError('Fusion export failed')
    names=item.GetFusionCompNameList()
    if len(names)!=1:raise RuntimeError('Unexpected Fusion name list')
    item.DeleteFusionCompByName(names[0])
    # Resolve may retain a default empty composition slot after deleting the last comp.
    # Validate the actual imported composition and final count rather than an intermediate zero.
    comp=item.ImportFusionComp(str(path))
    if not comp or item.GetFusionCompCount()!=1:raise RuntimeError('Reimport failed; exported backup retained at '+str(path))
    return comp
