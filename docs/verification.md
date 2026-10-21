# Delivery verification

## Expanded kitchen — 21 October 2026

Windows 11, Python 3.12.14, Arcade 3.3.3. The final source passed **50 tests**.
The rebuilt Windows ZIP passed **30 executable-level checks** after extraction
into a separate folder with spaces and removal of Python/source search paths.
The normal scene and F1 collision overlay were captured and visually inspected.

- Movement, animation, stable idle/facing, input, pause/reset/focus and rendering.
- Exact reachability of every station from spawn, accounting for the whole chef.
- Actual controller movement into every accessible face of every room/furniture
  obstacle, including stalled updates; no overlap or crossing allowed.
- All floor props have solids; table decorations fit inside their solid support.
- Chopping station E/Q routing remains feedback only. Food state is not created.
- The enlarged 1280 x 960 room and 300-pixel sidebar scale together for the display.
- Build includes the prepared background and item PNGs as well as chef frames.

![Verified packaged kitchen](images/kitchen_preview.png)

The ingredient, order and cutting implementations remain future work. This
verification was performed on this Windows machine, not teammates' computers.

## Initial player starter

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
