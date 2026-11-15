"""Bundled audio is complete and valid; the sound bank fails safe."""
import wave

import pytest

from restaurant.audio import AUDIO_DIR, CUES, MUSIC, ORDER_CUES, KitchenAudio
from restaurant.kitchen.days import DAYS


def test_every_named_sound_is_a_bundled_valid_wav():
    for name in (*CUES, *ORDER_CUES, *MUSIC):
        path = AUDIO_DIR / f"{name}.wav"
        assert path.is_file(), f"Missing {path}"
        with wave.open(str(path)) as file:
            seconds = file.getnframes() / file.getframerate()
            assert file.getnframes() > 200
        if name in MUSIC:
            assert 10 < seconds < 40          # a loop, not a one-shot
        elif name != "bubble":
            assert seconds < 2.0              # short cues never mask each other
    assert {day.music for day in DAYS} <= set(MUSIC)


def test_music_loops_join_without_a_click():
    for name in MUSIC:
        with wave.open(str(AUDIO_DIR / f"{name}.wav")) as file:
            frames = file.readframes(file.getnframes())
        first = int.from_bytes(frames[:2], "little", signed=True)
        last = int.from_bytes(frames[-2:], "little", signed=True)
        assert abs(first - last) < 2500, f"{name} would click when it repeats"


def test_muted_bank_records_cues_without_playing_and_rejects_unknown_names():
    audio = KitchenAudio()
    audio.muted = True
    audio.play("coin")
    audio.play("serve_fail")
    assert list(audio.history) == ["coin", "serve_fail"]
    with pytest.raises(KeyError):
        audio.play("explosion")
    with pytest.raises(KeyError):
        audio.play("bgm_warm")                # music is not a one-shot cue
    with pytest.raises(KeyError):
        audio.start_music("bgm_disco")


def test_music_follows_pause_and_mute(monkeypatch):
    started, stopped = [], []
    monkeypatch.setattr("arcade.play_sound", lambda sound, volume, loop=False: started.append(loop) or object())
    monkeypatch.setattr("arcade.stop_sound", lambda token: stopped.append(token))
    audio = KitchenAudio()
    audio.start_music("bgm_warm")
    audio.start_music("bgm_warm")             # same track: not restarted
    assert started == [True] and audio.music_name == "bgm_warm"
    audio.sync_music(False)                   # paused
    assert len(stopped) == 1
    audio.sync_music(True)
    assert started == [True, True]
    audio.muted = True
    audio.sync_music(True)
    assert len(stopped) == 2
    audio.muted = False
    audio.start_music("bgm_metal")
    assert audio.music_name == "bgm_metal" and started[-1] is True
    audio.stop_all()
    assert len(stopped) == 3
