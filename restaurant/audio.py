"""Arcade sound cues, the bubbling pot loop and background music.

One sound bank for the whole game:
- Food cues (pickup, plate, return, reject, bubble, advance...) are the food
  member's files from tools/prepare_kitchen_audio.py.
- Order, ambience and music cues come from tools/make_sounds.py.
Every file is loaded once. Cues play on events, never every frame. The
bubble and the music are single looping players that stop on pause, mute
and when the game is hidden. Without an audio device the game stays silent.
"""
from collections import deque
from pathlib import Path

import arcade

AUDIO_DIR = Path(__file__).resolve().parents[1] / "assets" / "audio"
CUES = ("pickup", "plate", "return", "accept", "serve", "reject", "bubble", "advance")
ORDER_CUES = ("order_bell", "serve_success", "coin", "serve_fail",
              "order_expired", "timer_tick", "day_complete", "transition", "drip", "spark")
MUSIC = ("bgm_warm", "bgm_metal")
ENEMY_CUES = ("ghost_warning", "ghost_steal", "ghost_recover", "blocker_warning",
              "blocker_arrive", "vampire_warning", "vampire_sweep", "vampire_bite", "shift_fail")
VOLUME = {"reject": 0.28, "order_bell": 0.5, "serve_success": 0.6,
          "coin": 0.32, "serve_fail": 0.35, "order_expired": 0.5, "timer_tick": 0.3,
          "day_complete": 0.6, "transition": 0.35, "drip": 0.28, "spark": 0.3}
MUSIC_VOLUME = 0.2


class KitchenAudio:
    def __init__(self):
        self.muted = False
        self.history = deque(maxlen=64)     # cue names requested, for checks
        self._sounds = {}
        for cue in (*CUES, *ORDER_CUES, *ENEMY_CUES, *MUSIC):
            try:
                self._sounds[cue] = arcade.load_sound(AUDIO_DIR / f"{cue}.wav")
            except Exception:                # missing file or no audio backend
                self._sounds[cue] = None
        self._bubble = None
        self._music = None
        self._music_name = None

    # ------------------------------------------------------------ cues
    def play(self, cue):
        if cue not in self._sounds or cue in MUSIC:
            raise KeyError(f"Unknown sound cue: {cue}")
        self.history.append(cue)
        if not self.muted and self._sounds[cue] is not None:
            try:
                arcade.play_sound(self._sounds[cue], volume=VOLUME.get(cue, 0.42))
            except Exception:
                pass

    def sync_bubble(self, cooking):
        if cooking and not self.muted and self._sounds["bubble"] is not None:
            if self._bubble is None:
                self._bubble = arcade.play_sound(self._sounds["bubble"], volume=0.28, loop=True)
        else:
            self.stop()

    def stop(self):
        """Stop the bubbling loop (pause, day change, ready pasta)."""
        if self._bubble is not None:
            arcade.stop_sound(self._bubble)
            self._bubble = None

    # ------------------------------------------------------------ music
    @property
    def music_name(self):
        return self._music_name

    def start_music(self, name):
        """Loop a track; asking for the track already chosen does nothing."""
        if name not in MUSIC:
            raise KeyError(f"Unknown music: {name}")
        if name == self._music_name:
            return
        self._stop_music_player()
        self._music_name = name
        self.sync_music(True)

    def sync_music(self, playing):
        """Music runs only while the game is playing and sound is on."""
        if playing and not self.muted and self._music_name:
            if self._music is None and self._sounds.get(self._music_name) is not None:
                try:
                    self._music = arcade.play_sound(self._sounds[self._music_name],
                                                    volume=MUSIC_VOLUME, loop=True)
                except Exception:
                    self._music = None
        else:
            self._stop_music_player()

    def _stop_music_player(self):
        if self._music is not None:
            try:
                arcade.stop_sound(self._music)
            except Exception:
                pass
            self._music = None

    def stop_all(self):
        """Window hidden or closed: silence everything."""
        self.stop()
        self._stop_music_player()
