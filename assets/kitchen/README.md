# Supplied kitchen and item pictures

These prepared PNGs are crops of the user's two supplied presentation sheets:

- Warm tiled kitchen, stove, bin, serving table and chopping board: 1408 x 768.
- Ingredient icons/crates, plate and pot: 1280 x 853.

These original crops were prepared without image generation. The current game
uses Arcade-drawn tiles for crisp, quiet flooring; `floor_tile.png`, `board.png`
and `back_wall.png` are legacy reference crops and are NOT loaded or drawn.
Separate original props have transparent backgrounds; only
background connected to crop edges and disconnected crop debris were removed.
The preview image is for inspecting assets and is not drawn in the game.

`restaurant_details.png` is a new transparent six-sprite atlas prepared with
the built-in imagegen tool, using the supplied kitchen as a style reference.
It provides the sink, pass counter, spice shelf, extractor, board and dining-room
hatch. Arcade crops its regions at load time; `restaurant/kitchen/scene.py`
records the coordinates. The original atlas is preserved with its transparency.
See [artwork notes and full prompt](../../docs/artwork_notes.md).

`crops.json` records exact top-left sheet coordinates. Recreate them, if needed:

```shell
python tools/prepare_kitchen.py PATH_TO_TILED_KITCHEN_JPEG PATH_TO_ITEMS_JPEG
```

Pillow is used only by that optional preparation tool and comes with Arcade.
The game imports Arcade and Python's standard library. Original uploads are
not needed to run/build it; the prepared PNGs are committed with the source.
Use these supplied assets under the original artwork's applicable permissions.
