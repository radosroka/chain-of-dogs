"""
Procedural background music synthesizer.
Inspired by the G-minor / dark-ambient style detected in the album.
Generates WAV files with numpy, plays them looping via paplay.
"""
import atexit
import os
import signal
import struct
import subprocess
import threading
import wave
import io
import numpy as np

SAMPLE_RATE = 22050
OUT_DIR = os.path.dirname(__file__)
AMBIENT_WAV = os.path.join(OUT_DIR, 'music_ambient.wav')
BATTLE_WAV  = os.path.join(OUT_DIR, 'music_battle.wav')
AMBIENT_OGG = os.path.join(OUT_DIR, 'music_ambient.ogg')
BATTLE_OGG  = os.path.join(OUT_DIR, 'music_battle.ogg')

# ── Musical constants (G minor) ──────────────────────────────────────────────
# G  A  Bb  C    D    Eb   F    G4   Bb4  D4   F4
G1, G2, D2 = 49.0, 98.0, 73.4
G3, A3, Bb3, C4, D4, Eb4, F4, G4 = 196.0, 220.0, 233.1, 261.6, 293.7, 311.1, 349.2, 392.0

PENTATONIC = [G3, Bb3, C4, D4, F4, G4, G3*2, Bb3*2]


# ── Low-level primitives ─────────────────────────────────────────────────────

def _t(dur):
    return np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)

def _sine(freq, dur, vol=1.0, detune=0.0):
    tt = _t(dur)
    return np.sin(2 * np.pi * (freq + detune) * tt) * vol

def _rich(freq, dur, vol=1.0):
    """Sine with warm harmonics — organ/pad quality."""
    tt = _t(dur)
    w  = (np.sin(2*np.pi*freq*tt)        * 1.00
        + np.sin(2*np.pi*freq*2*tt)      * 0.40
        + np.sin(2*np.pi*freq*3*tt)      * 0.15
        + np.sin(2*np.pi*freq*4*tt)      * 0.07
        + np.sin(2*np.pi*(freq*1.003)*tt)* 0.20  # slight detune for shimmer
        + np.sin(2*np.pi*(freq*0.997)*tt)* 0.20)
    return w / 1.82 * vol

def _env_adsr(n, a, d, s_lev, r):
    sr = SAMPLE_RATE
    a, d, r = int(a*sr), int(d*sr), int(r*sr)
    s = max(0, n - a - d - r)
    env = np.zeros(n)
    if a: env[:a]               = np.linspace(0, 1, a)
    if d: env[a:a+d]            = np.linspace(1, s_lev, d)
    env[a+d:a+d+s]              = s_lev
    if r: env[a+d+s:a+d+s+r]   = np.linspace(s_lev, 0, r)
    return env

def _fade(sig, fade_sec=2.0):
    f = int(fade_sec * SAMPLE_RATE)
    sig[:f]  *= np.linspace(0, 1, f)
    sig[-f:] *= np.linspace(1, 0, f)
    return sig

def _reverb(sig, room=0.55):
    delays = [(0.030, room),  (0.057, room*0.65),
              (0.101, room*0.40), (0.180, room*0.25)]
    out = sig.copy()
    for dt, g in delays:
        d = int(dt * SAMPLE_RATE)
        if d < len(out):
            out[d:] += sig[:-d] * g
    return out

def _norm(sig, peak=0.72):
    mx = np.max(np.abs(sig))
    return sig / mx * peak if mx > 0 else sig

def _to_wav(sig):
    buf = io.BytesIO()
    sig_i16 = (np.clip(sig, -1, 1) * 32767).astype(np.int16)
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(sig_i16.tobytes())
    return buf.getvalue()


# ── Chord pad builder ────────────────────────────────────────────────────────

def _pad(freqs, dur, vol=0.08, fade_sec=1.5):
    n = int(SAMPLE_RATE * dur)
    sig = np.zeros(n)
    for freq in freqs:
        osc = _rich(freq, dur, vol)
        sig[:len(osc)] += osc
    fade = min(int(fade_sec * SAMPLE_RATE), n // 2)
    sig[:fade]  *= np.linspace(0, 1, fade)
    sig[-fade:] *= np.linspace(1, 0, fade)
    return sig


# ── Ambient track ────────────────────────────────────────────────────────────

def _build_ambient(duration=120.0):
    sr = SAMPLE_RATE
    n  = int(sr * duration)
    tt = np.linspace(0, duration, n, endpoint=False)
    mix = np.zeros(n)

    # Layer 1 — deep drone (G1 + G2 + fifth)
    drone = (_sine(G1, duration, 0.18) +
             _sine(G2, duration, 0.13) +
             _sine(D2, duration, 0.07) +
             _sine(G2*2, duration, 0.05))
    # Slow breathing
    drone *= 0.75 + 0.25 * np.sin(2*np.pi*0.07*tt)
    mix += drone

    # Layer 2 — evolving chord pads (Gm → Cm → Eb → Bb → F)
    progression = [
        ([G3, Bb3, D4], 16.0),
        ([C4, Eb4, G4], 16.0),
        ([Eb4*0.5, G3, Bb3], 14.0),
        ([Bb3*0.5, D4*0.5, F4*0.5], 14.0),
        ([F4*0.5, A3, C4], 12.0),
        ([G3, Bb3, D4], 16.0),
        ([C4, Eb4, G4], 14.0),
        ([D4*0.5, F4*0.5, A3], 18.0),  # slight tension
    ]
    pos = 0.0
    for freqs, cdur in progression * 3:
        if pos >= duration: break
        cdur = min(cdur, duration - pos)
        sl, el = int(pos*sr), int((pos+cdur)*sr)
        seg = _pad(freqs, cdur, vol=0.06)
        mix[sl:sl+len(seg)] += seg
        pos += cdur * 0.92  # slight overlap

    # Layer 3 — sparse melody
    melody = [
        ( 0.0, G4,       5.0, 0.09),
        ( 7.0, D4,       4.0, 0.08),
        (13.0, Bb3,      6.0, 0.07),
        (21.0, C4,       4.5, 0.09),
        (27.0, G4,       3.5, 0.08),
        (32.0, F4,       5.0, 0.07),
        (39.0, D4,       4.0, 0.09),
        (45.0, Eb4,      3.0, 0.08),
        (50.0, G3,       7.0, 0.10),
        (59.0, Bb3,      4.5, 0.08),
        (65.0, C4,       5.0, 0.07),
        (72.0, D4,       4.0, 0.09),
        (78.0, G4,       6.0, 0.10),
        (86.0, F4,       4.0, 0.07),
        (92.0, G3,       8.0, 0.09),
       (102.0, Bb3,      5.0, 0.08),
       (109.0, G4,       duration-109.0, 0.07),
    ]
    for start, freq, ndur, vol in melody:
        if start >= duration: break
        ndur = min(ndur, duration - start)
        sl = int(start * sr)
        nn = int(ndur * sr)
        tt_note = np.linspace(0, ndur, nn, endpoint=False)
        note = (_sine(freq, ndur, 1.0) +
                _sine(freq*2, ndur, 0.25) +
                _sine(freq*3, ndur, 0.08))
        env = _env_adsr(nn, min(0.8, ndur*0.15), 0.5, 0.7, min(2.5, ndur*0.35))
        mix[sl:sl+nn] += note * env * vol

    # Layer 4 — occasional low bell hits
    for bt in [12, 32, 56, 80, 104]:
        if bt >= duration: break
        sl = int(bt * sr)
        bdur = 6.0
        nn = int(bdur * sr)
        bell = (_sine(G2*4, bdur, 1.0) + _sine(G2*6.27, bdur, 0.6) +
                _sine(G2*8.92, bdur, 0.3))
        env = _env_adsr(nn, 0.01, 0.3, 0.3, bdur - 0.31)
        mix[sl:sl+nn] += bell * env * 0.08

    mix = _reverb(mix, room=0.5)
    mix = _norm(mix, 0.70)
    mix = _fade(mix, 3.0)
    return mix


# ── Battle track (more intense) ──────────────────────────────────────────────

def _build_battle(duration=90.0):
    sr = SAMPLE_RATE
    n  = int(sr * duration)
    tt = np.linspace(0, duration, n, endpoint=False)
    mix = np.zeros(n)

    # Heavier drone
    drone = (_sine(G1, duration, 0.22) +
             _sine(G2, duration, 0.18) +
             _sine(D2*2, duration, 0.10))
    drone *= 0.85 + 0.15 * np.sin(2*np.pi*0.25*tt)
    mix += drone

    # Darker, faster chord movement (Gm - Dm - Gm - Eb - F)
    prog = [
        ([G3, Bb3, D4], 8.0),
        ([D4*0.5, F4*0.5, A3], 6.0),
        ([G3, Bb3, D4], 6.0),
        ([Eb4*0.5, G3, Bb3], 6.0),
        ([F4*0.5, A3, C4], 6.0),
    ]
    pos = 0.0
    for freqs, cdur in prog * 5:
        if pos >= duration: break
        cdur = min(cdur, duration - pos)
        sl = int(pos * sr)
        seg = _pad(freqs, cdur, vol=0.09, fade_sec=0.8)
        mix[sl:sl+len(seg)] += seg
        pos += cdur * 0.88

    # Rhythmic pulse — bass drum pattern every 2 beats (~0.75s apart)
    bpm = 80
    beat = 60.0 / bpm
    for i, bt in enumerate(np.arange(0, duration, beat)):
        sl = int(bt * sr)
        kdur = 0.35
        nn = int(kdur * sr)
        if sl + nn > n: break
        tt_k = np.linspace(0, kdur, nn)
        freq_sweep = 140 * np.exp(-18 * tt_k)
        phase = np.cumsum(2 * np.pi * freq_sweep / sr)
        kick = np.sin(phase)
        env = np.exp(-20 * tt_k)
        # Accent beats 1 and 3
        vol = 0.30 if i % 4 in (0, 2) else 0.15
        mix[sl:sl+nn] += kick * env * vol

    # Tension melody — faster, more chromatic
    tension = [
        ( 0, G4,   1.5, 0.10),
        ( 2, F4,   1.0, 0.09),
        ( 4, Eb4,  1.5, 0.10),
        ( 6, D4,   2.0, 0.11),
        ( 9, G3,   3.0, 0.10),
        (13, Bb3,  1.5, 0.09),
        (16, C4,   1.0, 0.10),
        (18, D4,   2.0, 0.11),
        (21, Eb4,  1.5, 0.09),
        (24, G4,   2.0, 0.10),
    ]
    for start, freq, ndur, vol in tension * 4:
        t_off = (start // 27) * 27 + (start % 27)
        if t_off >= duration: break
        ndur = min(ndur, duration - t_off)
        sl = int(t_off * sr)
        nn = int(ndur * sr)
        note = _sine(freq, ndur, 1.0) + _sine(freq*2, ndur, 0.20)
        env = _env_adsr(nn, 0.02, 0.1, 0.8, min(0.5, ndur*0.3))
        mix[sl:sl+nn] += note * env * vol

    mix = _reverb(mix, room=0.35)
    mix = _norm(mix, 0.72)
    mix = _fade(mix, 2.0)
    return mix


# ── WAV generation ───────────────────────────────────────────────────────────

def _to_ogg(wav_path, ogg_path):
    subprocess.run(
        ['ffmpeg', '-i', wav_path, '-c:a', 'libvorbis', '-q:a', '4', ogg_path, '-y'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


_gen_lock = threading.Lock()


def generate_all():
    """Generate WAV + OGG for both tracks if not already present."""
    with _gen_lock:
        if os.path.exists(AMBIENT_WAV) and os.path.exists(BATTLE_WAV):
            return

        print("  Composing ambient music...", flush=True)
        ambient = _build_ambient(120.0)
        with open(AMBIENT_WAV, 'wb') as f:
            f.write(_to_wav(ambient))
        _to_ogg(AMBIENT_WAV, AMBIENT_OGG)

        print("  Composing battle music...", flush=True)
        battle = _build_battle(90.0)
        with open(BATTLE_WAV, 'wb') as f:
            f.write(_to_wav(battle))
        _to_ogg(BATTLE_WAV, BATTLE_OGG)

        print("  Music ready.", flush=True)


# ── Playback ─────────────────────────────────────────────────────────────────

_player_proc = None
_player_lock  = threading.Lock()
_stop_event   = threading.Event()
_current_file = None


def _loop_thread(wav_file):
    global _player_proc
    while not _stop_event.is_set():
        with _player_lock:
            if _stop_event.is_set():
                break
            _player_proc = subprocess.Popen(
                ['paplay', wav_file],
                stderr=subprocess.DEVNULL,
            )
        _player_proc.wait()


def play(wav_file):
    global _current_file
    if wav_file == _current_file:
        return
    stop()
    _current_file = wav_file
    _stop_event.clear()
    threading.Thread(target=_loop_thread, args=(wav_file,), daemon=True).start()


def play_ambient():
    if os.path.exists(AMBIENT_WAV):
        play(AMBIENT_WAV)


def play_battle():
    if os.path.exists(BATTLE_WAV):
        play(BATTLE_WAV)


def stop():
    global _player_proc, _current_file
    _stop_event.set()
    _current_file = None
    with _player_lock:
        if _player_proc and _player_proc.poll() is None:
            _player_proc.terminate()
            _player_proc = None


def _cleanup():
    stop()


atexit.register(_cleanup)
signal.signal(signal.SIGTERM, lambda *_: _cleanup())
