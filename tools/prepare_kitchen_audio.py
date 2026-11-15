"""Generate original quiet, short UI sounds and a seamless pot loop."""
from array import array
from math import pi, sin
from pathlib import Path
import sys
import wave

RATE = 22050
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "audio"
NOTES = {
    "pickup": (520, 690),
    "plate": (420, 590),
    "return": (530, 390),
    "accept": (440, 550, 660),
    "serve": (520, 660, 780),
    "reject": (235, 175),
}


def save(name, samples):
    pcm = array("h", (round(sample * 32767) for sample in samples))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(OUTPUT / f"{name}.wav"), "wb") as file:
        file.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        file.writeframes(pcm.tobytes())


def cue(notes):
    for frequency in notes:
        for frame in range(RATE // 14):
            t = frame / RATE
            envelope = min(1, t / 0.005) * max(0, 1 - t * 14) ** 2
            yield 0.22 * envelope * sin(2 * pi * frequency * t)


def bubbles():
    for frame in range(RATE):
        t = frame / RATE
        sample = 0.0
        for start, pitch in ((0.04, 170), (0.29, 230), (0.44, 155), (0.72, 205)):
            age = t - start
            if 0 <= age < 0.18:
                envelope = sin(pi * age / 0.18) ** 2
                sample += 0.09 * envelope * sin(2 * pi * (pitch * age + 240 * age ** 2))
        yield sample


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, notes in NOTES.items():
        save(name, cue(notes))
    save("bubble", bubbles())
