# Delivery verification

Verified on 5 October 2026 with Windows 11, Python 3.12.14 and Arcade 3.3.3.
The completed GitHub checkout was verified again on 6 October 2026 in a fresh
environment: all 34 tests passed, including the graphical tests.

- Shared starter: **34 tests passed**, including real Arcade rendering.
- Compiled Windows app: **16 executable-level checks passed**.
- The delivered Windows ZIP was extracted into a separate folder containing
  spaces, then tested with Python/source paths removed from the environment.
  All 16 checks passed again. The executable used its own bundled runtime/assets.
- App checks exercise four-direction movement, animation and idle facing,
  counter collision, one interaction per press, pause, rendering and exit.
- The original player suite also covers input cancellation, diagonal speed,
  wall sliding, thin walls, bounds, dual movement keys, focus loss and reset.
- Shared record tests cover immutable snapshots, invalid IDs/revisions and
  compatibility between the future ingredient and order systems.

This is player-demo and shared-foundation verification. The ingredient/order
implementations have not been written or tested. No claim is made that the app
has been tested on other computers or operating systems.
