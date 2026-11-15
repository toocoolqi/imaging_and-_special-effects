"""Arcade sound cues and a single lifecycle-managed bubbling loop."""
from pathlib import Path

import arcade

AUDIO_DIR = Path(__file__).resolve().parents[1] / "assets" / "audio"
CUES = ("pickup", "plate", "return", "accept", "serve", "reject", "bubble", "advance")


class KitchenAudio:
    def __init__(self):
        self.muted = False
        self._sounds = {cue: arcade.load_sound(AUDIO_DIR / f"{cue}.wav") for cue in CUES}
        self._bubble = None

    def play(self, cue):
        if not self.muted:
            arcade.play_sound(self._sounds[cue], volume=0.28 if cue == "reject" else 0.42)

    def sync_bubble(self, cooking):
        if cooking and not self.muted:
            if self._bubble is None:
                self._bubble = arcade.play_sound(self._sounds["bubble"], volume=0.28, loop=True)
        else:
            self.stop()

    def stop(self):
        if self._bubble is not None:
            arcade.stop_sound(self._bubble)
            self._bubble = None
