import argparse
import importlib
import json
import platform
import sys
from pathlib import Path

from . import __version__
from .common import environment, write_json


def parser():
    p=argparse.ArgumentParser(description='Focus MV local toolkit. Inputs read-only; output paths must be new.')
    p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('doctor',help='Check configured Python and dependency imports');s.add_argument('--out');s.add_argument('--asr',action='store_true',help='Also check local Whisper runtime and model files, without inference/download')
    s=sub.add_parser('cache-check',help='Check whether a prior report and its artifacts can be reused');s.add_argument('report');s.add_argument('--inputs',nargs='+');s.add_argument('--out')
    s=sub.add_parser('probe',help='Metadata and optional compressed packet timing');s.add_argument('input');s.add_argument('--packets',action='store_true');s.add_argument('--out',required=True)
    s=sub.add_parser('frames',help='Exact zero-based decoded-frame thumbnails and contact sheet');s.add_argument('input');s.add_argument('--indices',required=True,help='Comma-separated zero-based indices');s.add_argument('--width',type=int,default=180);s.add_argument('--columns',type=int,default=6);s.add_argument('--out-dir',required=True)
    s=sub.add_parser('cover',help='Export one native-size frame and source manifest');s.add_argument('input');s.add_argument('--frame',type=int,required=True);s.add_argument('--out',required=True)
    s=sub.add_parser('paired-frames',help='Two-camera exact-frame contact sheet; B=A-offset');s.add_argument('a');s.add_argument('b');s.add_argument('--a-indices',required=True);s.add_argument('--offset-frames',type=int,required=True);s.add_argument('--width',type=int,default=180);s.add_argument('--out-dir',required=True)
    s=sub.add_parser('sync',help='Multi-window two-band audio offset candidates');s.add_argument('a');s.add_argument('b');s.add_argument('--window',type=float,default=6.);s.add_argument('--prior',type=float);s.add_argument('--radius',type=float,default=.5);s.add_argument('--anchors',type=int,default=5);s.add_argument('--min-corr',type=float,default=.6);s.add_argument('--fps',default='60000/1001');s.add_argument('--out',required=True)
    s=sub.add_parser('features',help='RMS and relative spectral features');s.add_argument('input');s.add_argument('--seconds',type=float,default=2.);s.add_argument('--out',required=True)
    s=sub.add_parser('qc',help='Full video/audio decode and expected-spec checks');s.add_argument('input');s.add_argument('--frames',type=int);s.add_argument('--size',help='WIDTHxHEIGHT');s.add_argument('--fps');s.add_argument('--out',required=True)
    s=sub.add_parser('audio-check',help='Waveform alignment or compressed audio packet identity');s.add_argument('a');s.add_argument('b');s.add_argument('--mode',choices=['waveform','packets'],default='waveform');s.add_argument('--max-lag',type=float,default=.5);s.add_argument('--min-corr',type=float,default=.98);s.add_argument('--max-offset-ms',type=float,default=2.);s.add_argument('--out',required=True)
    s=sub.add_parser('lyrics-align',help='Offline supplied-Chinese-text acoustic alignment candidates');s.add_argument('input');s.add_argument('--lyrics',required=True);s.add_argument('--model');s.add_argument('--threads',type=int,default=6);s.add_argument('--out',required=True)
    s=sub.add_parser('asr',help='Offline Chinese singing transcription candidates in an explicit range');s.add_argument('input');s.add_argument('--start',type=float,required=True);s.add_argument('--end',type=float,required=True);s.add_argument('--model');s.add_argument('--threads',type=int,default=6);s.add_argument('--out',required=True)
    s=sub.add_parser('lyrics-export',help='Export frame-snapped candidate SRT from alignment report');s.add_argument('alignment');s.add_argument('--fps',default='60000/1001');s.add_argument('--lead',type=float,default=.08);s.add_argument('--tail',type=float,default=.18);s.add_argument('--gap',type=float,default=.10);s.add_argument('--out-dir',required=True)
    s=sub.add_parser('retime-plan',help='Constant or smooth ramp slow-motion source mapping');s.add_argument('--frames',type=int,required=True);s.add_argument('--speed',type=float,default=.8);s.add_argument('--method',choices=['speedwarp','flow'],default='speedwarp');s.add_argument('--ramp-start',type=int,default=0);s.add_argument('--ramp-frames',type=int,default=0);s.add_argument('--source-start',type=int,default=0);s.add_argument('--fps',default='60000/1001');s.add_argument('--out',required=True)
    s=sub.add_parser('retime-check',help='Compare render probes with expected source-frame neighbors');s.add_argument('source');s.add_argument('render');s.add_argument('--plan',required=True);s.add_argument('--render-start',type=int,default=0);s.add_argument('--probes',type=int,default=12);s.add_argument('--search',type=int,default=3);s.add_argument('--tolerance',type=float,default=1.5);s.add_argument('--out',required=True)
    s=sub.add_parser('cache-match',help='Compare every requested cache/render frame');s.add_argument('cache');s.add_argument('render');s.add_argument('--frames',type=int,required=True);s.add_argument('--render-start',type=int,default=0);s.add_argument('--cache-start',type=int,default=0);s.add_argument('--min-corr',type=float,default=.995);s.add_argument('--max-mae',type=float,default=3.);s.add_argument('--out',required=True)
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        config=environment()
        if args.command=='doctor':
            modules={}
            for name in ['numpy','scipy','PIL','av','cv2']+(['faster_whisper','ctranslate2'] if args.asr else []):
                try:
                    m=importlib.import_module(name);modules[name]={'version':getattr(m,'__version__','unknown'),'path':m.__file__,'passed':True}
                except Exception as e:modules[name]={'passed':False,'error':str(e)}
            report={'toolkit_version':__version__,'python':sys.executable,'python_version':platform.python_version(),
                    'configured_python':config['python'],'modules':modules,'ffmpeg':config['ffmpeg'],
                    'passed':sys.version_info[:2]==(3,12) and all(m['passed'] for m in modules.values())}
            if args.asr:
                from .lyrics import model_files
                mp,files=model_files();report['local_asr_model']={'path':str(mp),'files':[{ 'name':f.name,'bytes':f.stat().st_size} for f in files], 'inference_performed':False}
            if args.out:write_json(args.out,report)
        elif args.command=='cache-check':
            from .common import check_cache
            report=check_cache(args.report,args.inputs)
            if args.out:write_json(args.out,report)
        elif args.command=='probe':
            from .media import probe_report
            report=probe_report(args.input,args.out,args.packets)
        elif args.command=='frames':
            from .media import frame_sheet
            report=frame_sheet(args.input,args.out_dir,[int(x) for x in args.indices.split(',')],args.width,args.columns)
        elif args.command=='cover':
            from .media import cover
            report=cover(args.input,args.frame,args.out)
        elif args.command=='paired-frames':
            from .media import paired_frames
            report=paired_frames(args.a,args.b,args.out_dir,[int(x) for x in args.a_indices.split(',')],args.offset_frames,args.width)
        elif args.command=='sync':
            from .sync import sync_report
            report=sync_report(args.a,args.b,args.out,window=args.window,prior=args.prior,radius=args.radius,anchors=args.anchors,fps=args.fps,min_corr=args.min_corr)
        elif args.command=='features':
            from .sync import audio_features
            report=audio_features(args.input,args.out,args.seconds)
        elif args.command=='qc':
            from .qc import decode_report
            size=tuple(int(x) for x in args.size.lower().split('x')) if args.size else None
            if size and (len(size)!=2 or min(size)<=0):raise ValueError('Size must be positive WIDTHxHEIGHT')
            report=decode_report(args.input,args.out,args.frames,size,args.fps)
        elif args.command=='audio-check':
            from .qc import compare_audio
            report=compare_audio(args.a,args.b,args.out,args.mode,args.max_lag,args.min_corr,args.max_offset_ms)
        elif args.command=='lyrics-align':
            from .lyrics import align_report
            report=align_report(args.input,args.lyrics,args.out,args.model,args.threads)
        elif args.command=='asr':
            from .lyrics import transcribe_report
            report=transcribe_report(args.input,args.out,args.start,args.end,args.model,args.threads)
        elif args.command=='lyrics-export':
            from .lyrics import export_subtitles
            report=export_subtitles(args.alignment,args.out_dir,args.fps,args.lead,args.tail,args.gap)
        elif args.command=='retime-plan':
            from .retime import plan_report
            report=plan_report(args.out,frames=args.frames,speed=args.speed,method=args.method,ramp_start=args.ramp_start,ramp_frames=args.ramp_frames,source_start=args.source_start,fps=args.fps)
        elif args.command=='retime-check':
            from .retime_qc import check_mapping
            report=check_mapping(args.source,args.render,args.plan,args.out,args.render_start,args.probes,args.search,args.tolerance)
        elif args.command=='cache-match':
            from .retime_qc import cache_match
            report=cache_match(args.cache,args.render,args.out,args.frames,args.render_start,args.cache_start,args.min_corr,args.max_mae)
        compact={k:report[k] for k in ['passed','cache_key','decoded_frames','lag_ms','correlation'] if k in report}
        if 'sync' in report:compact['sync']={k:report['sync'][k] for k in ['offset_seconds','nearest_offset_frames','status']}
        compact.update(command=args.command,output=getattr(args,'out',None) or getattr(args,'out_dir',None))
        if args.command=='doctor':compact['environment']=report
        if args.command=='cache-check':compact.update(reusable=report['reusable'],reasons=report['reasons'])
        print(json.dumps(compact,ensure_ascii=False,indent=2))
        return 0 if report.get('passed',True) else 2
    except Exception as exc:
        print(json.dumps({'error':type(exc).__name__,'message':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 1
