# Delivery verification

## Restaurant design and closer collisions — v0.4.0, 21 October 2026

Windows 11, Python 3.12.14, Arcade 3.3.3. **69 source tests** and **36 packaged
application checks** passed. The standalone ZIP was extracted into a new folder
with spaces, then run with Python/source paths removed from its environment.
The normal scene, resized scene and collision overlay were visually inspected.

- Kitchen area reduced about 14%, to 960 x 704; chef retains its native size.
- Plate island contains only the plate; pot sits over one stove burner.
- Matching sink, shelves, extractor, board and restaurant service hatch; the
  hatch visibly opens onto a dining room and retains the existing serve ID.
- All furniture bases checked from every accessible side. Exact station
  reachability includes the fixed 32 x 20 foot hitbox, offset 32 pixels down.
- Close approach verified: the feet stop within 2 pixels of a table base.
  Front/behind drawing order tested, including actual rendering behind a table.
- Input, animation, idle/facing, wall sliding, thin obstacles, pause/reset/focus,
  one E action per key press and feedback-only cutting/serving remain covered.
- Display-scale checks retain 100%, 125%, 150% and 200% cases. The actual default
  client was 1040 x 601 logical units / 1300 x 752 physical pixels at 125%.
  Its complete native outer frame remained inside the desktop work area.
- Runtime uses Arcade and Python's standard library. Artwork is bundled.
  Ingredient, cutting and order behavior remain future integration work.

![Verified standalone kitchen](images/kitchen_preview.png)

Earlier v0.1, v0.2 and v0.3 releases remain available for history. This verification
covers the local Windows machine, not other teammates' computers.
