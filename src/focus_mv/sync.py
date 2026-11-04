"""Source: stage2_audio.py normalized valid correlation, generalized to unknown offsets."""
import numpy as np
from scipy import signal

from .common import finite, fresh_output, make_report, rate, run_ffmpeg, write_json


def read_audio(path, sr=16000):
    result = run_ffmpeg(['-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', sr, '-f', 'f32le', 'pipe:1'])
    x = np.frombuffer(result.stdout, dtype='<f4').astype(np.float64)
    if not len(x) or not np.isfinite(x).all():
        raise ValueError('No valid decoded audio')
    return x


def filter_audio(x, low, high, sr):
    n = 1 << (len(x)-1).bit_length()
    spec = np.fft.rfft(x, n)
    freq = np.fft.rfftfreq(n, 1/sr)
    spec *= (freq >= low) & (freq <= high)
    return np.fft.irfft(spec, n)[:len(x)]


def corr_valid(x, y):
    if len(x) < len(y) or len(y) < 32 or np.std(y) < 1e-7:
        raise ValueError('Reference window too short or silent')
    y = y - y.mean()
    c = signal.fftconvolve(x, y[::-1], mode='valid')
    sums = np.r_[0., np.cumsum(x)]
    squares = np.r_[0., np.cumsum(x*x)]
    energy = (squares[len(y):]-squares[:-len(y)]) - (sums[len(y):]-sums[:-len(y)])**2/len(y)
    return c / np.sqrt(np.maximum(energy * np.dot(y, y), 1e-30))


def estimate(a, b, *, sr=16000, window=6., prior=None, radius=.5, anchors=5, min_corr=.6):
    window = finite(window, 'window')
    radius = finite(radius, 'radius')
    if window <= 0 or radius < 0 or not 2 <= anchors <= 30:
        raise ValueError('Window positive; radius nonnegative; anchors 2..30')
    n = round(window*sr)
    if min(len(a), len(b)) < n + 2:
        raise ValueError('Audio too short for requested window')
    prior = finite(prior, 'prior') if prior is not None else None
    # Search B windows in A, including negative offsets when B begins earlier.
    blo = max(0., -prior) if prior is not None else 0.
    bhi = min(len(b)/sr-window, len(a)/sr-window-prior) if prior is not None else len(b)/sr-window
    if bhi < blo:
        raise ValueError('No overlap under supplied prior')
    starts = np.linspace(blo, bhi, anchors)
    rows = []
    filtered = [(filter_audio(a, low, high, sr), filter_audio(b, low, high, sr), low, high)
                for low, high in [(150, 1500), (1500, 5500)]]
    for af, bf, low, high in filtered:
        for start in starts:
            bi = round(start*sr)
            lo = max(0, round((start+prior-radius)*sr)) if prior is not None else 0
            hi = min(len(a), round((start+prior+radius+window)*sr)) if prior is not None else len(a)
            if hi-lo < n:
                continue
            y = bf[bi:bi+n]
            if np.std(y) < 1e-7:
                continue
            c = corr_valid(af[lo:hi], y)
            best = int(np.argmax(c))
            peak = float(c[best])
            separated = c.copy()
            separated[max(0, best-round(.10*sr)):best+round(.10*sr)+1] = -np.inf
            second = float(np.max(separated)) if np.isfinite(separated).any() else None
            rows.append({'b_seconds': bi/sr, 'a_seconds': (lo+best)/sr,
                         'offset_seconds': (lo+best-bi)/sr, 'correlation': peak,
                         'second_peak_correlation': second,
                         'peak_margin': peak-second if second is not None else None,
                         'band_hz': [low, high]})
    accepted = [r for r in rows if r['correlation'] >= min_corr]
    if len(accepted) < 2:
        raise ValueError('No reliable sync candidate; use longer windows or a visual/manual prior')
    offsets = np.array([r['offset_seconds'] for r in accepted])
    median = float(np.median(offsets))
    spread = float(np.ptp(offsets))
    ambiguous = any(r['peak_margin'] is not None and r['peak_margin'] < .03 for r in accepted)
    return {'mapping': 'A_seconds = B_seconds + offset_seconds', 'offset_seconds': median,
            'accepted_windows': len(accepted), 'offset_range_ms': spread*1000, 'rows': rows,
            'status': 'candidate_needs_review' if ambiguous or spread > .020 else 'consistent_audio_candidate',
            'limitations': 'Audio arrival, codec delay, repeated music and camera drift affect estimates. Independently inspect motion/lip sync at several locations; no claim of zero visual error.'}


def sync_report(a, b, output, *, window=6., prior=None, radius=.5, anchors=5, fps='60000/1001', min_corr=.6):
    fresh_output(output, [a,b])
    if not 0 < min_corr <= 1:
        raise ValueError('min-corr must be in (0,1]')
    fps = rate(fps)
    report = make_report('sync.audio', [a,b], {'window': window, 'prior': prior, 'radius': radius,
                                            'anchors': anchors, 'fps': str(fps), 'min_corr': min_corr, 'sr':16000})
    report['sync'] = estimate(read_audio(a), read_audio(b), window=window, prior=prior,
                              radius=radius, anchors=anchors, min_corr=min_corr)
    delta = report['sync']['offset_seconds']
    report['sync'].update(fps=str(fps), offset_frames_float=delta*float(fps),
                          nearest_offset_frames=round(delta*float(fps)))
    write_json(output, report)
    return report


def audio_features(path, output, seconds=2.):
    fresh_output(output, [path])
    seconds = finite(seconds, 'seconds')
    if seconds <= 0:
        raise ValueError('Window seconds must be positive')
    report = make_report('analysis.audio_features', [path], {'seconds':seconds,'sr':16000,'nfft':2048,'hop':160})
    x = read_audio(path)
    if len(x) < 2048:
        raise ValueError('Audio too short')
    framed = np.lib.stride_tricks.sliding_window_view(x,2048)[::160]
    sp = np.abs(np.fft.rfft(framed*np.hanning(2048)))
    freq = np.fft.rfftfreq(2048,1/16000)
    rms = np.sqrt(np.mean(framed*framed,axis=1))
    flux = np.maximum(np.diff(np.log1p(sp),axis=0),0).mean(axis=1)
    t = np.arange(len(rms))*.01+2048/32000
    rows=[]
    for start in np.arange(0,len(x)/16000,seconds):
        mask=(t>=start)&(t<start+seconds)
        fm=(t[1:]>=start)&(t[1:]<start+seconds)
        if not mask.any():continue
        row={'start_seconds':float(start),'end_seconds':min(float(start+seconds),len(x)/16000),
             'rms_dbfs':float(20*np.log10(max(np.sqrt(np.mean(rms[mask]**2)),1e-12))),
             'positive_log_spectral_flux':float(np.mean(flux[fm])) if fm.any() else 0.}
        for label,lo,hi in [('low',60,250),('mid',250,2000),('high',2000,7000)]:
            row[label]=float(sp[mask][:,(freq>=lo)&(freq<hi)].mean())
        rows.append(row)
    report.update(duration_seconds=len(x)/16000,features=rows,
                  scope='Relative spectral features and window RMS; not LUFS, confirmed beats, instruments, emotion or musicological analysis.')
    write_json(output,report)
    return report
