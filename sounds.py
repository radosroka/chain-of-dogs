"""
Terminal sound synthesis via PulseAudio (paplay).
All audio generated in pure Python — no extra dependencies.
Playback is non-blocking (background threads).
"""
import io
import math
import os
import random
import struct
import subprocess
import threading
import wave

_DICE_ROLL_FILE = os.path.join(os.path.dirname(__file__), 'dice_roll.ogg')

SAMPLE_RATE = 22050
_enabled = True


def _wav_bytes(samples: list[float]) -> bytes:
    """Convert [-1.0, 1.0] float samples to a WAV byte string."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        clipped = [max(-1.0, min(1.0, s)) for s in samples]
        w.writeframes(struct.pack(f'<{len(clipped)}h',
                                  *[int(s * 32767) for s in clipped]))
    return buf.getvalue()


def _play(samples: list[float]):
    if not _enabled:
        return
    data = _wav_bytes(samples)
    threading.Thread(
        target=lambda: subprocess.run(
            ['paplay', '--raw', f'--rate={SAMPLE_RATE}',
             '--format=s16le', '--channels=1'],
            input=struct.pack(f'<{len(samples)}h',
                              *[int(max(-1.0, min(1.0, s)) * 32767) for s in samples]),
            stderr=subprocess.DEVNULL,
        ),
        daemon=True,
    ).start()


# ── Primitive generators ────────────────────────────────────────────────

def _sine_sweep(f0: float, f1: float, dur: float, vol: float = 0.4) -> list[float]:
    n = int(SAMPLE_RATE * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f0 * (f1 / f0) ** t          # exponential sweep
        env = (1.0 - t) ** 1.5              # decay envelope
        phase += 2 * math.pi * freq / SAMPLE_RATE
        out.append(math.sin(phase) * vol * env)
    return out


def _sine_tone(freq: float, dur: float, vol: float = 0.3) -> list[float]:
    n = int(SAMPLE_RATE * dur)
    return [math.sin(2 * math.pi * freq * i / SAMPLE_RATE) * vol *
            (1.0 - i / n) ** 1.5
            for i in range(n)]


def _noise_burst(dur: float, vol: float = 0.15, cutoff: float = 0.1) -> list[float]:
    """White noise with a simple one-pole lowpass (cutoff in 0..1)."""
    n = int(SAMPLE_RATE * dur)
    prev = 0.0
    out = []
    for i in range(n):
        env = (1.0 - i / n) ** 2
        white = (random.random() * 2 - 1) * vol * env
        prev = prev + cutoff * (white - prev)
        out.append(prev)
    return out


def _sawtooth_sweep(f0: float, f1: float, dur: float, vol: float = 0.25) -> list[float]:
    n = int(SAMPLE_RATE * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f0 * (f1 / f0) ** t
        env = (1.0 - t) ** 1.5
        phase = (phase + freq / SAMPLE_RATE) % 1.0
        out.append((2 * phase - 1) * vol * env)
    return out


def _mix(*tracks) -> list[float]:
    length = max(len(t) for t in tracks)
    out = [0.0] * length
    for track in tracks:
        for i, s in enumerate(track):
            out[i] += s
    return out


def _delay(samples: list[float], seconds: float) -> list[float]:
    pad = int(SAMPLE_RATE * seconds)
    return [0.0] * pad + samples


# ── Named sounds ────────────────────────────────────────────────────────

def play_dice_roll():
    if not _enabled or not os.path.exists(_DICE_ROLL_FILE):
        return
    threading.Thread(
        target=lambda: subprocess.run(
            ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', _DICE_ROLL_FILE],
        ),
        daemon=True,
    ).start()


def play_click():
    _play(_sine_sweep(900, 400, 0.07, 0.18))


def play_march():
    _play(_mix(
        _sine_sweep(140, 65, 0.18, 0.4),
        _noise_burst(0.12, 0.08, 0.08),
    ))


def play_forced():
    thud1 = _sine_sweep(160, 60, 0.15, 0.45)
    thud2 = _delay(_sine_sweep(140, 55, 0.13, 0.35), 0.13)
    noise = _noise_burst(0.18, 0.1, 0.1)
    _play(_mix(thud1, thud2, noise))


def play_rest():
    _play(_mix(
        _sine_sweep(520, 660, 0.25, 0.12),
        _sine_tone(440, 0.4, 0.08),
    ))


def play_forage():
    _play(_mix(
        _noise_burst(0.22, 0.18, 0.35),
        _sine_sweep(280, 500, 0.2, 0.08),
    ))


def play_battle():
    clash1 = _mix(
        _noise_burst(0.08, 0.35, 0.9),
        _sawtooth_sweep(200, 80, 0.25, 0.22),
    )
    clash2 = _delay(_mix(
        _noise_burst(0.06, 0.25, 0.85),
        _sawtooth_sweep(180, 70, 0.2, 0.17),
    ), 0.09)
    tail = _delay(_sine_sweep(600, 200, 0.15, 0.1), 0.16)
    _play(_mix(clash1, clash2, tail))


def play_danger():
    _play(_sawtooth_sweep(300, 150, 0.3, 0.22))


def play_start():
    s1 = _sine_sweep(330, 440, 0.15, 0.12)
    s2 = _delay(_sine_sweep(440, 550, 0.15, 0.1), 0.14)
    s3 = _delay(_sine_sweep(550, 660, 0.2, 0.08), 0.28)
    _play(_mix(s1, s2, s3))


def play_victory():
    s1 = _sine_sweep(440, 550, 0.15, 0.15)
    s2 = _delay(_sine_sweep(550, 660, 0.15, 0.13), 0.14)
    s3 = _delay(_sine_sweep(660, 880, 0.3,  0.1),  0.28)
    chord = _delay(_mix(
        _sine_tone(440, 0.5, 0.08),
        _sine_tone(550, 0.5, 0.06),
        _sine_tone(660, 0.5, 0.05),
    ), 0.55)
    _play(_mix(s1, s2, s3, chord))


def play_defeat():
    s1 = _sine_sweep(300, 200, 0.3, 0.15)
    s2 = _delay(_sine_sweep(200, 130, 0.4, 0.12), 0.28)
    s3 = _delay(_sine_sweep(130, 80,  0.5, 0.1),  0.62)
    _play(_mix(s1, s2, s3))
