"""Synthesise every game sound from maths (Python standard library only).

Run from the repository root:

    python -m tools.make_sounds

Writes 16-bit mono WAV files to assets/audio/ (order cues, ambience and
music; the food cues there come from tools/prepare_kitchen_audio.py and are
not touched). Nothing is downloaded or
sampled from a recording: each sound is built from sine/square/triangle
waves and noise shaped by volume envelopes, so the team created and owns
all audio. The output is deterministic (fixed random seed).

How a sound is made
- An oscillator gives the raw tone (sine = soft, triangle = flute-like,
  square = bright "chiptune").
- An ADSR-style envelope shapes loudness over time (fast attack + decay
  sounds struck, like a bell; slow attack sounds like a swell).
- A pitch sweep (frequency changing during the note) makes pops, drips
  and thuds. Filtered noise makes clicks, zaps and whooshes.
- Layers are mixed, then normalised so nothing clips.
"""
from math import exp, pi, sin
from pathlib import Path
import random
import struct
import wave

RATE = 22050
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "audio"
rng = random.Random(2026)


def midi(note):
    """MIDI note number -> frequency in Hz (69 = A4 = 440 Hz)."""
    return 440.0 * 2 ** ((note - 69) / 12)


def osc(kind, phase):
    """One cycle of a waveform; phase is in cycles (0..1 repeating)."""
    p = phase % 1.0
    if kind == "sine":
        return sin(2 * pi * p)
    if kind == "square":
        return 1.0 if p < 0.5 else -1.0
    if kind == "pulse":          # thin 25% pulse: softer chiptune lead
        return 1.0 if p < 0.25 else -1.0
    if kind == "triangle":
        return 4 * abs(p - 0.5) - 1.0
    raise ValueError(kind)


def note(freq, seconds, kind="sine", volume=1.0, attack=0.005, decay=None, sweep_to=None):
    """A single enveloped tone. decay = exponential time constant (None = flat)."""
    count = int(seconds * RATE)
    out = []
    phase = 0.0
    for i in range(count):
        t = i / RATE
        f = freq if sweep_to is None else freq + (sweep_to - freq) * (i / max(1, count - 1))
        phase += f / RATE
        env = min(1.0, t / attack) if attack else 1.0
        env *= exp(-t / decay) if decay else 1.0
        env *= min(1.0, (seconds - t) / 0.008)      # tiny fade-out avoids a click
        out.append(osc(kind, phase) * env * volume)
    return out


def noise(seconds, volume=1.0, decay=None, smooth=0.0):
    """White noise; smooth (0..1) is a one-pole low-pass that darkens it."""
    count = int(seconds * RATE)
    out, last = [], 0.0
    for i in range(count):
        t = i / RATE
        raw = rng.uniform(-1, 1)
        last = last * smooth + raw * (1 - smooth)
        env = exp(-t / decay) if decay else 1.0
        env *= min(1.0, (seconds - t) / 0.008)
        out.append(last * env * volume)
    return out


def bell(freq, seconds, volume=1.0):
    """Struck bell: inharmonic partials, each decaying faster than the last."""
    parts = ((1.0, 1.0, 0.45), (2.76, 0.5, 0.25), (5.4, 0.25, 0.12), (8.93, 0.12, 0.06))
    return mix(*[note(freq * ratio, seconds, "sine", amp * volume, 0.002, tau)
                 for ratio, amp, tau in parts])


def mix(*layers):
    out = [0.0] * max(len(layer) for layer in layers)
    for layer in layers:
        for i, value in enumerate(layer):
            out[i] += value
    return out


def at(seconds, layer):
    """Delay a layer by `seconds` of silence."""
    return [0.0] * int(seconds * RATE) + layer


def normalise(samples, peak=0.85):
    top = max(1e-9, max(abs(v) for v in samples))
    return [v * peak / top for v in samples]


def save(name, samples, peak=0.85):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = normalise(samples, peak)
    with wave.open(str(OUTPUT / f"{name}.wav"), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(RATE)
        file.writeframes(b"".join(struct.pack("<h", int(v * 32767)) for v in data))
    return len(data) / RATE


# ----------------------------------------------------------------- effects

def effects():
    return {
        # Orders
        "order_bell": mix(bell(midi(88), 0.7), at(0.16, bell(midi(93), 0.9, 0.9))),
        "serve_success": mix(noise(0.05, 0.5, decay=0.02),                 # drawer "cha"
                             at(0.05, bell(midi(95), 0.5, 0.9)),           # "ching"
                             at(0.14, bell(midi(100), 0.8, 1.0)),
                             at(0.14, note(midi(88), 0.5, "sine", 0.25, decay=0.2))),
        "coin": mix(note(midi(95), 0.05, "square", 0.5, decay=0.04),
                    at(0.045, note(midi(100), 0.22, "square", 0.5, decay=0.09))),
        "serve_fail": mix(note(110, 0.32, "square", 0.6, attack=0.01),
                          note(116.5, 0.32, "square", 0.6, attack=0.01)),   # detuned = harsh
        "order_expired": mix(note(midi(67), 0.22, "triangle", 0.9, decay=0.2),
                             at(0.2, note(midi(64), 0.22, "triangle", 0.9, decay=0.2)),
                             at(0.4, note(midi(60), 0.5, "triangle", 1.0, decay=0.3))),
        "timer_tick": note(1100, 0.04, "sine", 1.0, attack=0.001, decay=0.012),
        "day_complete": mix(*[at(0.11 * i, note(midi(n), 0.3, "pulse", 0.5, decay=0.22))
                              for i, n in enumerate((72, 76, 79, 84))],
                            *[at(0.48, note(midi(n), 1.2, "triangle", 0.5, attack=0.02, decay=0.6))
                              for n in (72, 76, 79, 84)],
                            at(0.48, bell(midi(96), 1.2, 0.5))),
        # Scenes
        "transition": [v * min(1.0, i / (0.3 * RATE)) * min(1.0, (0.6 * RATE - i) / (0.25 * RATE))
                       for i, v in enumerate(noise(0.6, 1.0, smooth=0.96))],
        "drip": mix(note(1050, 0.1, "sine", 1.0, attack=0.001, decay=0.03, sweep_to=380),
                    at(0.05, note(700, 0.08, "sine", 0.3, attack=0.001, decay=0.03, sweep_to=300))),
        "spark": mix(noise(0.16, 1.0, decay=0.04), note(3200, 0.1, "square", 0.25, decay=0.03),
                     at(0.07, noise(0.06, 0.6, decay=0.02))),
    }


# ----------------------------------------------------------------- music

def render_loop(bpm, bars, tracks):
    """Mix note events into a seamless loop: tails wrap round to the start."""
    beat = 60.0 / bpm
    total = int(bars * 4 * beat * RATE)
    out = [0.0] * total
    for start_beat, samples in tracks:
        offset = int(start_beat * beat * RATE)
        for i, value in enumerate(samples):
            out[(offset + i) % total] += value
    return out


def music(bpm, chords, melody, lead, drums):
    beat = 60.0 / bpm
    tracks = []
    for bar, (root, tones) in enumerate(chords):
        base = bar * 4
        for step, length in ((0, 1.0), (1.5, 0.5), (2, 1.0), (3, 1.0)):       # bass groove
            pitch = root + (7 if step == 3 else 0)
            tracks.append((base + step, note(midi(pitch), length * beat, "triangle", 0.55,
                                             attack=0.01, decay=0.35)))
        for eighth in range(8):                                               # arpeggio
            pitch = tones[(0, 1, 2, 1)[eighth % 4]] + 12
            tracks.append((base + eighth * 0.5, note(midi(pitch), 0.45 * beat, "sine", 0.16,
                                                     attack=0.005, decay=0.12)))
        for step in drums.get("kick", ()):
            tracks.append((base + step, note(120, 0.14, "sine", 0.7, attack=0.002, decay=0.05,
                                             sweep_to=45)))
        for step in drums.get("hat", ()):
            tracks.append((base + step, noise(0.04, 0.12, decay=0.012)))
    for start, length, pitch in melody:
        tracks.append((start, note(midi(pitch), length * beat * 0.95, lead, 0.3,
                                   attack=0.012, decay=0.5)))
    return render_loop(bpm, len(chords), tracks)


C, AM, F, G, DM, E = ((48, (60, 64, 67)), (45, (57, 60, 64)), (41, (53, 57, 60)),
                      (43, (55, 59, 62)), (50, (57, 62, 65)), (40, (52, 56, 59)))
WARM_MELODY = (
    (0, 1, 76), (1, 1, 79), (2, 1.5, 84), (3.5, .5, 79),
    (4, 1, 81), (5, 1, 76), (6, 2, 72),
    (8, 1, 77), (9, 1, 81), (10, 1.5, 84), (11.5, .5, 81),
    (12, 1, 79), (13, 1, 83), (14, 2, 86),
    (16, 1, 88), (17, 1, 84), (18, 1.5, 79), (19.5, .5, 76),
    (20, 1, 81), (21, 1, 84), (22, 2, 88),
    (24, 1, 86), (25, 1, 81), (26, 1.5, 77), (27.5, .5, 74),
    (28, 1, 79), (29, 1, 83), (30, 1, 86), (31, 1, 83),
)
METAL_MELODY = (
    (0, .5, 81), (.5, .5, 84), (1, 1, 88), (2, .5, 86), (2.5, .5, 84), (3, 1, 81),
    (4, .5, 77), (4.5, .5, 81), (5, 1, 84), (6, 1, 81), (7, 1, 77),
    (8, .5, 79), (8.5, .5, 84), (9, 1, 88), (10, .5, 86), (10.5, .5, 84), (11, 1, 79),
    (12, 1, 79), (13, 1, 83), (14, 1, 86), (15, 1, 83),
    (16, .5, 81), (16.5, .5, 84), (17, 1, 88), (18, .5, 91), (18.5, .5, 88), (19, 1, 84),
    (20, 1, 77), (21, .5, 81), (21.5, .5, 84), (22, 1, 89), (23, 1, 84),
    (24, .5, 86), (24.5, .5, 89), (25, 1, 81), (26, 1, 86), (27, 1, 77),
    (28, 1, 76), (29, 1, 80), (30, 1, 83), (31, 1, 88),
)


def build():
    report = {}
    for name, samples in effects().items():
        report[name] = save(name, samples)
    # Cosy major-key loop for the warm restaurant; a brisker minor-key loop
    # with drums for the steel one.
    report["bgm_warm"] = save("bgm_warm", music(96, (C, AM, F, G, C, AM, DM, G), WARM_MELODY,
                                                "triangle", {"hat": (1, 3)}), peak=0.6)
    report["bgm_metal"] = save("bgm_metal", music(112, (AM, F, C, G, AM, F, DM, E), METAL_MELODY,
                                                  "pulse", {"kick": (0, 2), "hat": (0.5, 1.5, 2.5, 3.5)}),
                               peak=0.6)
    for name, seconds in report.items():
        print(f"{name}.wav  {seconds:.2f}s")
    return report


if __name__ == "__main__":
    build()
