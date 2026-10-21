# Supplied kitchen and item pictures

These prepared PNGs are crops of the user's two supplied presentation sheets:

- Warm tiled kitchen, stove, bin, serving table and chopping board: 1408 x 768.
- Ingredient icons/crates, plate and pot: 1280 x 853.

No image generation was used. `back_wall.png` keeps the upper room without the
sheet's captions or cut-off foreground furniture. `floor_tile.png` repeats in
Arcade to expand its floor. Separate props have transparent backgrounds; only
background connected to crop edges and disconnected crop debris were removed.
The preview image is for inspecting assets and is not drawn in the game.

`crops.json` records exact top-left sheet coordinates. Recreate them, if needed:

```shell
python tools/prepare_kitchen.py PATH_TO_TILED_KITCHEN_JPEG PATH_TO_ITEMS_JPEG
```

Pillow is used only by that optional preparation tool and comes with Arcade.
The game imports Arcade and Python's standard library. Original uploads are
not needed to run/build it; the prepared PNGs are committed with the source.
Use these supplied assets under the original artwork's applicable permissions.
