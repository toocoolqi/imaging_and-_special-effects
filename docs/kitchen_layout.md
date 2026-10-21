# Expanded tiled kitchen

The kitchen uses the warm tiled background from the supplied image. Its room
is now **1280 x 960 world pixels**, increased from 900 x 720. The original back
wall/counter row is preserved; floor tiles from that image extend the room.
The complete view has a 300-pixel order sidebar. The window scales the whole
view to fit the display, without changing movement speed or collision sizes.

![Kitchen preview](images/kitchen_preview.png)

## What is in the room

- Four supplied ingredient-crate pictures.
- A plate/preparation table with plate, milk and noodles pictures.
- A separate chopping table with the supplied board and knife picture.
- A serving table displaying sandwich and tomato pictures.
- A stove and pot, a bin, and the original wall furniture/appliances.

These are display props. E previews a nearby station; it does not collect,
cut, cook, discard or serve food. The player still has no hold-item animations.

## Change the map in one place

Edit `restaurant/kitchen/layout.py`. Each `KitchenProp` gives an ID, PNG name,
center `(x, y)`, visible width/height, and whether it stands on the floor.
The renderer and solid furniture rectangles use the same record. Keep prepared
images in `assets/kitchen/`; the build includes that whole directory.

`ROOM_SOLIDS` closes the left, right and bottom edges and the complete original
back wall/counter row. Furniture uses conservative full visual rectangles:
the chef cannot overlap its legs/front, walk behind the wall artwork, or leave
the room through the bottom. The sidebar is outside the kitchen.

Small decorations set `solid=False` and name their supporting table/stove.
They inherit that furniture's solid rectangle. A new object on the FLOOR must
have its own solid rectangle. Do not make it decorative without collision.
Press F1 to see all solid outlines and station ranges over the artwork.

The chef's fixed collision rectangle is 31.2 x 55.9 world pixels. Leave wider
aisles than that in both axes. Approach markers belong on clear floor beside
furniture. Run the tests after moving a table or marker: they check exact target
reachability from spawn, including the chef's whole body, and press the actual
controller against every accessible side of every obstacle.

## Chopping integration point

`InteractionTarget("chopping_board", "chop", 795, 318)` is the reserved floor
approach point below the chopping table. `ingredient_id` is empty. An E press
reaches `GameView.handle_interaction("interact", target)` with `kind == "chop"`.
It currently displays feedback only. Connect future cutting state there using
the cutting system's public method; keep food state out of PlayerController.
Q still applies only to the plate station. No cutting timer or recipe exists yet.

The existing box IDs/IngredientId contract remain unchanged for team integration.
The supplied crate images depict sandwich, tomato, noodles and milk, while the
agreed game IDs remain lettuce, tomato, bread and cheese. The pictures do not
provide those ingredients today. Agree the final food list/art with the group
before implementing collection, rather than silently changing shared IDs.

## Checks and rebuilding

Run `python -m pytest tests -q` in your configured environment on a desktop.
`python main.py --self-test artifacts/kitchen-check` also captures the real
rendered scene and F1 overlay and reports application checks in `self-test.json`.
The same argument works on the packaged `PlayerDemo.exe`.

Rebuild using `python -m PyInstaller --noconfirm PlayerDemo.spec` on Windows.
Share the whole `dist/PlayerDemo` folder, including `_internal`, as a ZIP.
See the main README for environment setup and controls.
