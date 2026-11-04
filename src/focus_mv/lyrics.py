"""Local-only ASR/alignment. Extracted from stage2_asr.py and lyric V1 align.py.

No historical script import, implicit model download, project edits or song-specific fixes.
"""
import json
import math
import unicodedata
from fractions import Fraction
from pathlib import Path

from .common import environment,finite,fresh_output,make_report,rate,sha256,write_json,run_ffmpeg


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC',text).lower() if c.isalnum())


def model_files(model_path=None):
    selected = model_path or environment()['asr_model']
    if not selected:
        raise ValueError('Set CODEX_RESOLVE_ASR_MODEL to a local Whisper model directory; no download is attempted')
    path=Path(selected).resolve(strict=True)
    files=[path/n for n in ['config.json','model.bin','tokenizer.json','vocabulary.txt']]
    if not all(p.is_file() for p in files):raise ValueError('Incomplete local Whisper model; no download is attempted')
    return path,files


def load_model(path,threads=6):
    from faster_whisper import WhisperModel
    if not 1<=threads<=64:raise ValueError('CPU threads must be 1..64')
    return WhisperModel(str(path),device='cpu',compute_type='int8',cpu_threads=threads,
                        num_workers=1,local_files_only=True)


def audio_window(path,start,end):
    import numpy as np
    start=finite(start,'start');end=finite(end,'end')
    if start<0 or end<=start:raise ValueError('Audio window requires 0 <= start < end')
    p=run_ffmpeg(['-v','error','-i',path,'-ss',start,'-t',end-start,'-vn','-ac','1','-ar','16000','-f','f32le','pipe:1'])
    x=np.frombuffer(p.stdout,'<f4').copy()
    if len(x)<round((end-start)*16000)-160:raise ValueError('Audio window extends beyond decoded source')
    if not len(x) or not np.isfinite(x).all() or float(np.std(x))<1e-7:raise ValueError('Audio window is empty, invalid or silent')
    return x


def validate_windows(data):
    if data.get('language','zh')!='zh':raise ValueError('This version validates Chinese lyrics only')
    windows=data.get('windows',[])
    if not isinstance(windows,list) or not windows:raise ValueError('Provide nonempty windows list')
    seen=set();previous=-1.
    for window in windows:
        start=finite(window['start'],'start');end=finite(window['end'],'end')
        if start<0 or end<=start or end-start>28 or start<previous:
            raise ValueError('Windows must have increasing starts, nonnegative bounds and duration <=28 seconds')
        previous=start
        lines=window.get('lines',[])
        if not isinstance(lines,list) or not lines:raise ValueError('Every window needs supplied lyric lines')
        for line in lines:
            key=line.get('id');text=line.get('text')
            if not isinstance(key,str) or not key or key in seen:raise ValueError('Line IDs must be unique nonempty strings')
            if not isinstance(text,str) or not normalized(text):raise ValueError('Empty normalized lyric text')
            if any(c.isalnum() and not ('\u3400'<=c<='\u9fff') for c in unicodedata.normalize('NFKC',text)):
                raise ValueError('Chinese characters and punctuation only in this version; mixed lyrics need a separate adapter')
            seen.add(key)
    return windows


def map_words(words,lines,start,end):
    chars=[];warnings=[]
    for word in words:
        text=normalized(word['word'])
        if not text:continue
        a=start+float(word['start']);b=start+float(word['end']);p=float(word.get('probability',0.))
        if not all(math.isfinite(v) for v in [a,b,p]) or not start-.03<=a<=b<=end+.03:
            raise ValueError('Model produced invalid or out-of-window timing')
        if len(text)>1:warnings.append('multi_character_token_shared_interval')
        for char in text:chars.append({'char':char,'start':a,'end':b,'probability':p,
                                      'interval_scope':'word/token interval; not phoneme precision'})
    expected=''.join(normalized(line['text']) for line in lines)
    if ''.join(c['char'] for c in chars)!=expected:raise ValueError('Aligned text does not exactly match supplied normalized lyrics')
    result=[];cursor=0
    for line in lines:
        count=len(normalized(line['text']));cc=chars[cursor:cursor+count];cursor+=count
        issues=[]
        if cc[-1]['end']<=cc[0]['start']:issues.append('zero_duration')
        if min(c['probability'] for c in cc)<.2:issues.append('low_token_probability')
        if cc[0]['start']<start+.04 or cc[-1]['end']>end-.04:issues.append('window_edge_contact')
        result.append({'id':line['id'],'text':line['text'],'vocal_start':cc[0]['start'],'vocal_end':cc[-1]['end'],
                       'characters':cc,'issues':issues,'review_status':'machine_candidate_needs_review'})
    return result,sorted(set(warnings))


def align_report(path,lyrics_file,output,model_path=None,threads=6):
    import numpy as np
    from faster_whisper.tokenizer import Tokenizer
    fresh_output(output,[path,lyrics_file]);data=json.loads(Path(lyrics_file).read_text(encoding='utf-8-sig'))
    windows=validate_windows(data);mp,resources=model_files(model_path)
    report=make_report('lyrics.align',[path,lyrics_file],{'language':'zh','threads':threads,'device':'cpu','compute_type':'int8',
          'model_path':str(mp),'max_window_seconds':28,'timing_scope':'supplied text acoustic candidate'},resources)
    model=load_model(mp,threads);tokenizer=Tokenizer(model.hf_tokenizer,model.model.is_multilingual,task='transcribe',language='zh')
    rows=[];window_reports=[]
    for w in windows:
        x=audio_window(path,w['start'],w['end']);features=model.feature_extractor(x);nf=features.shape[-1]-1
        if features.shape[-1]>3000:raise ValueError('Audio features exceed Whisper context; split windows')
        features=np.pad(features,((0,0),(0,3000-features.shape[-1])))
        text='，'.join(line['text'] for line in w['lines'])+'。'
        words=model.find_alignment(tokenizer,[tokenizer.encode(text)],model.encode(features),nf)[0]
        mapped,warnings=map_words(words,w['lines'],float(w['start']),float(w['end']))
        rows.extend(mapped);window_reports.append({'start':w['start'],'end':w['end'],'line_ids':[l['id'] for l in w['lines']],
                                                 'warnings':warnings,'features_frames':nf})
    report.update(passed=True,needs_review=True,lines=rows,windows=window_reports,
       limitations='Supplied-text forced alignment can fit wrong lyrics to music. Exact text reconstruction is not recognition accuracy. Singing, repetitions, instrumental boundaries and token-shared times need visual/listening review; no song-specific timing corrections applied.')
    write_json(output,report);return report


def transcribe_report(path,output,start,end,model_path=None,threads=6):
    fresh_output(output,[path]);start=finite(start,'start');end=finite(end,'end')
    if end-start>120:raise ValueError('Use explicit ASR ranges <=120 seconds; cache each range')
    mp,resources=model_files(model_path)
    report=make_report('lyrics.transcribe',[path],{'start':start,'end':end,'language':'zh','threads':threads,
                       'device':'cpu','compute_type':'int8','model_path':str(mp)},resources)
    x=audio_window(path,start,end);model=load_model(mp,threads)
    segments,info=model.transcribe(x,language='zh',beam_size=5,vad_filter=False,condition_on_previous_text=False,word_timestamps=True)
    rows=[]
    for s in segments:
        rows.append({'start':start+s.start,'end':start+s.end,'text':s.text,'avg_logprob':s.avg_logprob,
                     'no_speech_prob':s.no_speech_prob,'words':[{'text':w.word,'start':start+w.start,'end':start+w.end,'probability':w.probability} for w in s.words or []]})
    report.update(passed=True,needs_review=True,segments=rows,limitations='Machine singing transcription, not verified lyrics or human listening. No automatic acceptance or engineering changes.')
    write_json(output,report);return report


def subtitle_rows(lines,fps='60000/1001',lead=.08,tail=.18,gap=.10):
    fps=rate(fps);lead=finite(lead,'lead');tail=finite(tail,'tail');gap=finite(gap,'gap')
    if min(lead,tail,gap)<0:raise ValueError('Subtitle margins cannot be negative')
    if not lines:raise ValueError('No aligned lines')
    result=[];previous_end=0
    for i,line in enumerate(lines):
        a=finite(line['vocal_start'],'vocal_start');b=finite(line['vocal_end'],'vocal_end')
        if a<0 or b<=a:raise ValueError('Invalid vocal bounds; review alignment before export')
        start=max(0,round(Fraction(str(a-lead))*fps));end=round(Fraction(str(b+tail))*fps)
        if i+1<len(lines):end=min(end,round(Fraction(str(float(lines[i+1]['vocal_start'])-gap))*fps))
        if start<previous_end or end<=start:raise ValueError('Overlapping or nonpositive subtitle cues; refine windows/timing explicitly')
        previous_end=end
        result.append({'id':line['id'],'text':line['text'],'start_frame':start,'end_frame_exclusive':end,
                       'start_seconds':float(start/fps),'end_seconds':float(end/fps),
                       'review_status':line.get('review_status','candidate_needs_review')})
    return result


def srt_time(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


def export_subtitles(alignment,output_dir,fps='60000/1001',lead=.08,tail=.18,gap=.10):
    out=fresh_output(output_dir,[alignment]);data=json.loads(Path(alignment).read_text(encoding='utf-8-sig'))
    if data.get('tool')!='lyrics.align' or not data.get('passed'):raise ValueError('Expected successful lyrics.align report')
    rows=subtitle_rows(data['lines'],fps,lead,tail,gap)
    # A subtitle cache must also expire when the upstream audio, supplied lyrics or model changes.
    upstream=[s['path'] for s in data.get('sources',[])+data.get('resources',[])]
    report=make_report('lyrics.export',[alignment],{'fps':str(rate(fps)),'lead':lead,'tail':tail,'gap':gap},upstream)
    out.mkdir(parents=True)
    target=out/'lyrics_candidate.srt'
    with target.open('x',encoding='utf-8-sig') as f:
        for i,row in enumerate(rows,1):f.write(f'{i}\n{srt_time(row["start_seconds"])} --> {srt_time(row["end_seconds"])}\n{row["text"]}\n\n')
    report.update(passed=True,needs_review=True,cues=rows,artifacts=[{'file':target.name,'sha256':sha256(target)}],
                  scope='Frame-snapped subtitle candidates, not confirmed lyric timing or an editable Resolve Text+ track.')
    write_json(out/'manifest.json',report);return report
