# Ingredient artwork

`Pixel Cooking Game Asset Sheet.png` is the original reference, preserved as-is.
`sprites/` contains 12 separate transparent PNGs:

- Food: `sandwich`, `tomato`, `noodles`, `milk`.
- Boxes: `box_sandwich`, `box_tomato`, `box_noodles`, `box_milk`.
- Station artwork: `plate`, `pot_empty`, `pot_cooking`, `pot_cooked`.

`sprites_preview.png` shows all exports on a light background. `sprites.json`
lists file names, dimensions and atlas regions. Load PNGs relative to the module's
location and use nearest-neighbor filtering when displaying pixel artwork.

The transparent `sprites_atlas.png` was prepared with the built-in image tool,
so these are AI-assisted cutouts rather than pixel-identical source crops. Tiny
details and faint steam can differ from the original. The extraction prompt is
saved in `extraction_prompt.txt`. `split_sprites.ps1` slices that atlas without
rescaling, removes faint alpha halos, and adds two pixels of transparent padding.
To reproduce the individual files on Windows:

```powershell
powershell -File assets/ingredients/split_sprites.ps1
```

The shared gameplay IDs match this artwork: `sandwich`, `tomato`, `noodles`,
and `milk`. All four foods and boxes are loaded by the ingredient renderer.
Pots are saved for possible later use; cooking remains outside this milestone.
