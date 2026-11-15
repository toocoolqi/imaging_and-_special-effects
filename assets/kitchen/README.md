# Kitchen artwork

## The four day kitchens

Each day loads its own art set, with **identical file names** in every folder:

| Folder | Day | How it is made from the warm pictures below |
| --- | --- | --- |
| `warm_overgrown/` | 1 | Rot, chipped paint, damp streaks, mould, moss, vines, cracked tiles, puddles |
| `warm_clean/` | 2 | The pictures resized onto the game's pixel grid |
| `metal_damaged/` | 3 | Steel + rust on edges and seams, drips, dents, hanging doors, missing tiles, exposed wiring |
| `metal_clean/` | 4 | Wood and teal paint recoloured to brushed steel, cobalt trim, white tiles |

Every file sits exactly on the art grid of `restaurant/pixel_art.py` (one
image pixel = one art pixel = two world pixels), so the game draws it 1:1.
`room.png` is the whole floor, walls and rear upstands (480 x 352, opaque).
Clean and damaged twins have pixel-identical outlines, so damage can never
change a footprint or hide a station. Crates, plate, pot and food are never
copied here: they stay Member 2's sprites in `assets/ingredients/sprites/`.
`manifest.json` lists every file with its size, source picture and crop.

Rebuild all four sets (Pillow only, fixed seeds, identical output each time):

```shell
python -m tools.build_kitchens
```

No image generation was used for the four sets: they are image processing
(HSV colour masks, luminance recolouring, noise masks, morphology, blending)
plus procedurally drawn pixel-art detail. See `tools/build_kitchens.py` and
`tools/kitchen_fx.py`. If a folder is missing, the game falls back to the
pictures below and the Arcade-shape floor in `restaurant/kitchen/details.py`.

## Supplied kitchen and item pictures (source art)

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
