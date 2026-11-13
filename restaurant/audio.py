"""Short synthesized cues bundled with the game."""
from pathlib import Path

import arcade

AUDIO_DIR = Path(__file__).resolve().parents[1] / "assets" / "audio"


class GameAudio:
    def __init__(self, enabled):
        self.muted = not enabled
        self.sounds = {}
        self.bubbles = None

    def play(self, name, *, loop=False):
        if self.muted:
            return None
        if name not in self.sounds:
            self.sounds[name] = arcade.load_sound(AUDIO_DIR / f"{name}.wav")
        return arcade.play_sound(self.sounds[name], volume=.26 if loop else .4, loop=loop)

    def set_bubbling(self, active):
        if active and self.bubbles is None:
            self.bubbles = self.play("bubble", loop=True)
        elif not active and self.bubbles is not None:
            arcade.stop_sound(self.bubbles)
            self.bubbles = None

    def toggle(self):
        self.muted = not self.muted
        if self.muted:
            self.set_bubbling(False)
