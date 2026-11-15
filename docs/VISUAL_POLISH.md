# Visual polish and integration

The original images remain in `assets/`. The game now renders the chef,
furniture, food and floor on one 608 x 352 grid, covering the same 1216 x 704
world coordinates as before. Movement and station positions are unchanged.

`restaurant/pixel_art.py` owns this display work. `PixelCanvas.begin()` selects
the art target; `present()` enlarges it with nearest sampling and returns to
the screen. `draw_pixel_texture(texture, rectangle)` is the common sprite
draw function. It gives sprites solid edges, a little local contrast and the
same colour precision. It samples large source images down once, and never
smooths enlarged pixels. Texture uploads are reused across days and restarts.

The normal window uses a two-screen-pixel block for each art pixel where the
desktop has room. Smaller displays and arbitrary resized windows still show
the entire game, though fractional scaling cannot give every pixel identical
width. Labels are drawn afterward at their actual screen size, not reduced
with the artwork. `artwork_viewport(window)` is shared by the menu, game and
mouse hit testing so Windows display scaling is applied only once.

## Entry point and controls

`python main.py` opens `MainMenu`, with mouse Play/Quit and Enter/Esc shortcuts.
`create_window(visible=False)` still opens the game directly for integration
tests; pass `show_menu=True` to exercise the startup path. The menu's callback
creates a new `GameView`. Existing in-game controls remain in
[FINAL_GAMEPLAY.md](FINAL_GAMEPLAY.md).

## Held items

Food state still belongs to `IngredientSystem`. After actions, `GameView`
passes `held=state.held`, `carrying_plate=...` and `chopping=...` to
`PlayerController.set_visual_state()`. The controller only controls appearance.
It starts the pickup lift once when the held ID changes, follows each frame's
palm, and resets the standing pose on release. `KitchenScene` draws the food
at `hand_anchor`, at `hand_item_size`, with `draw_grip()` over its edge. When
facing away, food is drawn before the body. Plate and chopping poses remain
separate. Do not maintain another inventory inside the player.

## Fixed kitchen equipment

Use `KitchenProp.fixed_to_back_wall=True` for equipment fitted against the
back wall. The measured front edge stays unchanged while the solid extends to
`FLOOR_TOP`. The stove, sink and service counter use this flag. Center islands
and crates do not. F1 displays the actual solids; interaction circles are not
collision boundaries. Keep the visible rear trim in `kitchen/details.py` in
step with any new wall fixture.

## Verify a change

Run `python -m pytest -q` on a desktop, then
`python main.py --self-test artifacts/check`. The second command uses the
actual menu, clicks Play, checks held-food pickup, and exercises movement,
standing, carrying, chopping, cooking and service. It saves screenshots and
`self-test.json`. Run the same argument on a packaged EXE after extracting its
entire ZIP. A passing source test does not replace checking the packaged app.
