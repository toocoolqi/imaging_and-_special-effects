# Classic Chef frames

These PNGs were extracted from the user's uploaded `image.png` (1536x1024),
specifically Chef 1 / Classic Chef. They retain the artwork from that image;
no replacement character was generated. Original usage rights remain with the
source asset; this project does not assert a new license for the artwork.

- `down_0..3`, `up_0..3`, `left_0..3`, `right_0..3`: the four walk frames in each
  labeled column, ordered top-left, top-right, bottom-left, bottom-right.
- `idle_0..3`: the four front-facing idle samples; the demo uses `idle_0`.
- `frames.json`: original source crop centers and prepared canvas dimensions.
- `frame_preview.png`: all prepared frames on a contrasting background.

**No hold-item columns are extracted or loaded.** The full presentation image is
not needed by the game and is not included in the deliverable.

The input was a presentation sheet with labels and a partially transparent,
shaded background, rather than a clean sprite atlas. Crops are 56x92 pixels.
Boundary-connected low-opacity/blue-grey background pixels were removed while
keeping the chef's colors and outlines. Some source antialiasing remains; these
are practical extracted frames, not reconstructed original 32x32 source art.

The supplied files are ready to use. To reproduce extraction, run this from the
root with the original supplied image:

```shell
python tools/prepare_chef.py "path/to/image.png"
```

That optional utility uses Pillow, already included as an Arcade dependency.
Runtime game code imports only Arcade and Python's standard library. The utility
requires the exact 1536x1024 source dimensions; do not use a resized screenshot.
