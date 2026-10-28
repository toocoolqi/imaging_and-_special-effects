# Member 2 ingredient and plate system

Step 1 implements pure state logic in `models.py` and `system.py`, using the
existing immutable records from `restaurant.shared.contracts`. No Arcade import
or window is needed.

```python
from restaurant.ingredients import IngredientSystem

ingredients = IngredientSystem()
ingredients.collect("noodles")
ingredients.add_to_plate()
plate = ingredients.snapshot().plate  # PlateSnapshot(("noodles",), revision=1)
```

The public actions are `collect`, `add_to_plate`, `remove_from_plate`, `discard`,
`snapshot`, `clear_plate(expected_revision)`, and `reset`. The plate holds four
ingredients, including duplicates. Removal returns the newest ingredient to an
empty hand. Discard clears held food first, otherwise the entire plate.

Plate mutations increment its revision. Failed actions and hand-only changes
leave the revision unchanged. Clearing a matching empty plate succeeds without
incrementing it; stale clearing fails without changing anything. Only session
reset returns the revision to zero. Pass `snapshot().plate` directly to the order
system; after successful serving, clear using the checked revision.

Run the state tests from the repository root:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ingredients.py -q
```

## Independent demo

From the repository root:

```powershell
.venv\Scripts\python.exe -m demos.ingredients_demo
```

Keys 1-4 collect sandwich, tomato, noodles, and milk. A adds to the plate, Q
retrieves the newest item, B discards, R resets, and Esc closes. Each physical
press performs one action. Focus loss releases the demo's tracked keys.
The screen shows the hand, insertion order, capacity, revision, and latest result.
All four food sprites, their boxes, and the plate load from
`assets/ingredients/sprites/`. Missing artwork falls back to labeled colors.
The demo has no dependency on PlayerController or OrderSystem.

The shared IDs now match the supplied artwork: `sandwich`, `tomato`, `noodles`,
and `milk`. Members 1 and 3 need these updated definitions. The old ingredient
IDs are rejected. The team's order recipe catalogue still needs agreement for
these items; the previous assembly recipes no longer apply.

## Renderer handoff to Member 1

```python
from restaurant.ingredients.renderer import IngredientRenderer

# Once, while setting up the view:
renderer = IngredientRenderer()
# During drawing, after the kitchen/player and before the sidebar:
renderer.draw(ingredients.snapshot(), player.position, targets)
```

The renderer accepts the shared `IngredientSnapshot`, player position, and tuple
of `InteractionTarget` records. It owns no gameplay state. Box artwork is drawn
80 pixels above each interaction point; plate artwork is drawn 85 pixels above
the plate interaction point, matching the agreed kitchen station layout.
It draws labels, food beside the player, and numbered plate slots. It does not
draw the chef or order sidebar. Keep its import out of the package root so pure
state consumers do not import Arcade.

Member 3 can read `ingredients.snapshot().plate` directly. For example, a noodles
and milk plate after two additions is `PlateSnapshot(("noodles", "milk"), 2)`.
Drawing never clears a plate; GameView coordinates successful serving and clearing.

Run the rendering/input checks with
`.venv\Scripts\python.exe -m pytest tests/test_ingredients_demo.py -q` on a
graphics-capable desktop. Automated checks exercise collection, full-plate
feedback, removal, both discard paths, reset, key repeat, focus loss, read-only
drawing, and rendering without artwork.

Production wiring belongs to Member 1 and remains pending. See
`docs/member_2_ingredients_plate.md` for the complete agreement.
