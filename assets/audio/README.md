# Kitchen sounds

The seven bundled mono WAV files were synthesized for this project with Python's
standard library. No external samples or third-party licenses apply. Use and
redistribute them with the game. Regenerate with `python tools/prepare_kitchen_audio.py`.

## Orders, ambience and music

These files were also synthesized for this project, by `python -m tools.make_sounds`
(sine, triangle, square and noise waves shaped by volume envelopes). No samples
or third-party licenses apply.

| File | Played when |
| --- | --- |
| `order_bell` | A new order arrives (its timer starts) |
| `serve_success`, `coin` | A correct order is served and paid |
| `serve_fail` | A plate nobody ordered is sent back |
| `order_expired` | A taken order runs out of time |
| `timer_tick` | Once a second while a taken order has under 10 s left |
| `day_complete` | The day's gold target is reached |
| `transition` | Fading into the next kitchen |
| `drip`, `spark` | Water drops (overgrown kitchen), sparks (damaged steel kitchen) |
| `bgm_warm`, `bgm_metal` | Looping music for the warm and the steel kitchens |
