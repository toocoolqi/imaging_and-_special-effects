# Team work plan — 3 November 2026

This is the current assignment. It supersedes the older member guides for the
next milestone. Read this file, then your one member guide below.

| Owner | Responsibility | Guide |
| --- | --- | --- |
| Member 1 — player/integration | Shared game, controls, map switching, collisions, final verification | [Player and integration](team/01_player_integration.md) |
| Member 2 — task2 / food | Food art, plate lifecycle, pots/bubbling, sidebar orders, serving and sound | [Food and orders](team/02_food_cooking_orders.md) |
| Member 3 — kitchens | Warm and metallic kitchens, plus overgrown/damaged variants | [Kitchen environments](team/03_kitchen_environments.md) |

These are role labels, not invented teammate names. The task2 branch is the food
member's existing work. There are currently three remote branches: main, task2,
and feature/kitchen-background. The shared baseline combines their history using
normal merges; no branch history is replaced or force-pushed.

## What works in this combined baseline

- Native-size Classic Chef movement, four-direction walk/idle and facing.
- DPI-aware resizable kitchen, foot collisions and furniture depth sorting.
- The task2 IngredientSystem and its independent ingredients demo.
- Task2 crates, food, plate and empty-pot art in the warm kitchen. They match the
  existing wood/teal style. Its cooking/cooked pot sprites are retained for later.
- E at a crate collects food; E at the plate adds it; Q removes the newest item;
  E at the bin discards held food first, otherwise clears the plate. R resets
  player and food together. A small held icon uses no hold-item animation.

The warm kitchen is the visual reference in [the current screenshot](images/kitchen_preview.png).
Kitchen 2, environment damage, real cooking, moving/reusable plates, order
completion and sound are the NEXT work assigned below; this baseline does not
claim those features already exist. Service/chopping currently show feedback.
There is no curtain asset on task2: its crates/cartons and food assets were the
matching items available to reuse.

## How everyone starts after the shared update

Save your own local edits first; commit them on your branch before pulling.
Never reset or discard somebody else's work to obtain this baseline.

    git fetch origin
    git switch YOUR_EXISTING_BRANCH
    git pull --ff-only origin YOUR_EXISTING_BRANCH
    py -3.12 -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    .venv\Scripts\python.exe main.py

Replace YOUR_EXISTING_BRANCH with main, task2 or feature/kitchen-background.
If you have unpublished local commits and the pull refuses, use a normal merge
with origin/YOUR_EXISTING_BRANCH, resolve both versions, and rerun tests. Do not
force-push. New work should use a feature branch from the updated shared baseline.
See CONTRIBUTING.md for the normal commit/PR workflow.

## Shared contract

Runtime is Python Arcade plus the standard library. Use the existing packages;
keep food state out of PlayerController and drawing code. Current food IDs are
sandwich, tomato, noodles, milk, matching task2. Existing box target IDs now use
those names too. Keep plate, bin, serve and chopping_board stable across maps.

Member 2 owns food/orders/audio behavior. Member 3 provides visuals and map
measurements; Member 1 integrates maps and verifies movement. Shared contracts
and GameView changes must be coordinated before either member edits them.

## The target milestone

All four environment variants are selectable. A player can collect food, put it
on a plate, cook a simple pot recipe with visible bubbling, carry a prepared
plate to the service hatch, complete a sidebar order, retain the empty plate,
and return it to its table. There are sounds for these essential actions.
Acceptance examples and precise defaults are in each guide.

Before handoff run pytest, the independent ingredient demo and the combined game.
Include screenshots, a short controls list and any unfinished work in your PR.
One successful test of a component is not proof the combined game works.
