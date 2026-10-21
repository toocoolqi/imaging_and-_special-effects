# Kitchen detail artwork

The chef, original tables, stove, bin, pantry crates, pot and plate retain the
user's supplied artwork. The floor and architectural trim are editable Arcade
shapes. They avoid enlarging a small JPEG floor patch.

The additional details were generated once with the **built-in imagegen tool**,
using the original warm kitchen sheet as a style reference. No CLI/API fallback
was used. Saved project asset: [restaurant_details.png](../assets/kitchen/restaurant_details.png).
This 1536 x 1024 RGBA atlas contains six separate transparent sprites; it is
shipped unchanged. Its transparent background was inspected, and every used
region was checked in the running game. Runtime extraction uses Arcade's
`Texture.crop`, with bounds in `restaurant/kitchen/scene.py`.

## Final generation prompt

Use case: stylized-concept. Asset type: transparent game sprite atlas for a Python Arcade restaurant kitchen. The reference is STYLE reference only. Create SIX neatly separated standalone game sprites in an EXACT 2-column by 3-row grid, landscape canvas 1536x1024 (each cell 768 wide x approx341 high). Each sprite fully contained within its cell, centered, generous transparent padding, no overlaps, no captions, no labels, no text, no characters, no floor or backdrop. REAL transparent background. Use the reference's original warm copper wood worktops, teal cabinet fronts, cream glazed pottery, dark brown pixel outlines and low top-down orthographic camera; match the separate table and stove in the BOTTOM of the reference. Straight front edges, no isometric angle. Crisp carefully constructed pixel-art sprite look, consistent pixel density and restrained highlights, no blurred painterly texture. Top left cell: a broad restaurant sink counter, warm wood top with inset stainless steel basin, faucet, small soap bottle and draining grooves, teal cupboard doors and a neat striped towel hanging front. Top right cell: a broad service counter with warm wood top and teal cabinets, one tiny brass service bell at right, folded cream tea towel at left, otherwise CLEAR EMPTY counter, no food and no plates. Middle left cell: wall-mounted wooden spice shelf with arranged colorful jars, two stacks of cream cups, tiny trailing herb pot; shelves only, no wall. Middle right cell: steel extractor hood for a single stove, wooden utensil rail extending a little to the right with three hanging utensils, coherent placement, no wall. Bottom left cell: ONE clean wooden chopping board viewed low top-down, with one knife resting flat, standalone object with fully transparent surrounding area, NO table underneath. Bottom right cell: wide wooden-framed restaurant serving hatch/window, dark sage dining room visible THROUGH it with two tiny warm pendant lamps and distant booth outlines, a wooden lower sill and three small blank order tickets tucked along sill. No food, no counter below this window. The entire hatch frame is opaque and rectangular with transparent space around it. Keep each of the six objects entirely inside its specified grid cell; no extra objects between cells.
