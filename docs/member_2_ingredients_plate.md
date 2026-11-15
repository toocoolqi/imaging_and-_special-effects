> Historical guide. For the current November assignment, read [TEAM_PLAN.md](TEAM_PLAN.md) and its three linked role guides.

# Member 2 — Ingredient + Plate System

Read your personal instructions first, then the shared agreement. This file is standalone: the shared section is deliberately repeated in all three guides. Keep those shared sections identical when changing the plan.

## Your role in plain language

You own food and plate state. A box supplies an ingredient, the chef's hand holds one ingredient, and the plate stores up to four. You make those state changes reliable and visible. The player system tells you an action occurred; the order system receives a read-only plate snapshot.

Your branch is `feature/member-2-ingredients-plate`. Start it after the shared foundation merges.

## Your files and deliverables

Own restaurant/ingredients/models.py, system.py, renderer.py and __init__.py; assets/ingredients/; demos/ingredients_demo.py; tests/test_ingredients.py.

Deliver pure state logic plus a renderer. Keep Arcade imports in renderer/demo, so another member can test collecting and plate matching without opening a window.

Define `IngredientRenderer.draw(state: IngredientSnapshot, player_position: tuple[float, float], targets: tuple[InteractionTarget, ...]) -> None` in renderer.py. It draws food-box labels, the held ingredient beside the chef, and plate contents at the plate target. Constructor may load your assets but takes no gameplay state. Member 1 calls it from GameView. Do not draw the chef or order sidebar.

## Exact action behavior

| Action | Success | Ordinary failure |
|---|---|---|
| collect(id) | Empty hand becomes id; plate unchanged | Hand occupied: leave state unchanged |
| add_to_plate() | Append held ingredient; empty hand; revision +1 | Empty hand or full plate: unchanged |
| remove_from_plate() | Pop newest ingredient into empty hand; revision +1 | Occupied hand or empty plate: unchanged |
| discard() | If holding: clear hand only. Else: clear nonempty plate, revision +1 | Empty hand and empty plate: unchanged |
| clear_plate(revision) | Matching revision: clear nonempty plate, revision +1; hand unchanged | Stale revision: return false, unchanged |

For discard with nothing to discard, return ActionResult(false, "Nothing to discard"). For a matching revision on an empty plate, clear_plate returns true without a revision increment. Use clear feedback such as “Hand is full”, “Plate is full”, or “Added tomato”. Do not raise exceptions for these normal gameplay outcomes.

Validate collect's ingredient ID even when the hand is occupied. A programmer sending an invalid ID should receive ValueError, rather than a misleading “Hand is full”.

## Build it in this order

1. **Models:** implement storage for held ingredient, plate list and revision. Capacity is always 4. Keep mutable lists private. Share only frozen snapshots containing tuples.
2. **Actions:** implement collect, add, remove, discard and revision-checked clearing. Follow the table exactly. Return ActionResult for normal actions.
3. **Snapshots:** make a fresh snapshot of current state. A previously obtained snapshot must remain unchanged after later actions. Do not expose a public mutable plate list.
4. **Reset:** clear hand/plate and set revision to 0 only when the session resets. Ordinary serving/discarding increments revisions instead.
5. **Renderer:** distinguish all four ingredients with text and color before adding artwork. Show plate contents in insertion order and show capacity, e.g. 2/4. Drawing has no side effects.
6. **Demo:** use direct action buttons/keys to exercise your system without PlayerController or OrderSystem. In this demo only, keys 1–4 collect sandwich/tomato/noodles/milk; A adds, Q removes, B discards, R resets. Display hand, contents, revision and latest result.
7. **Handoff:** give Member 1 your renderer import/signature and give Member 3 a PlateSnapshot example. The shared records already define the format; do not invent JSON or another conversion layer.

## How to test your part independently

Run `python -m pytest tests/test_ingredients.py` and `python -m demos.ingredients_demo`.

Automated checks must cover:
- Initial empty state/revision 0; collect each valid ID and reject invalid IDs.
- A second collection fails without overwriting the held ingredient.
- Add succeeds once, empties hand, appends contents and increments revision.
- Adding with empty hand or to a capacity-4 plate changes nothing, including the hand/revision.
- Duplicates are allowed; the fifth ingredient cannot be added.
- Remove uses last-in-first-out order and transfers into the hand. Occupied hand blocks removal.
- Bin discards held food before touching plate. With empty hand it clears the plate once.
- Snapshots remain unchanged after later mutations.
- Successful matching-revision clearing preserves held food; stale clearing changes nothing.
- Empty clearing behavior and reset follow the agreed revision rules.

Use pytest assertions on snapshots/results, not visual guesses. In the manual demo, confirm all box labels, hand feedback, ingredient icons/text, full-plate feedback, and readable plate contents. Demo controls are shortcuts for testing; production controls stay E/Q.

## What you must not implement or edit

Do not move the chef, choose nearby targets, generate orders, decide order matches, award score, or clear a plate automatically when drawing it. Do not add cooking flags, chopping, finite stock, multiple plates, or a carried-plate mechanic. Do not edit player/order modules, shared contracts/settings or GameView without coordination.

Your system trusts that GameView already checked proximity. Do not add a second, inconsistent distance check inside collect/add methods.

## Your handoff checklist

- [ ] All agreed methods and return values are implemented.
- [ ] State module imports without Arcade or a window.
- [ ] Capacity, duplicates, failure behavior and revision checks are tested.
- [ ] Renderer works with placeholders and assets load from repository-relative paths.
- [ ] Independent demo runs using the documented controls.
- [ ] PR includes test results and a short demo capture or detailed observed results.
- [ ] Member 1 has renderer details; Member 3 can read your snapshot without private access.

## Your integration checklist and acceptance criteria

- [ ] E at a box collects exactly one ingredient if hand is empty.
- [ ] E at the plate transfers held food once; Q retrieves the latest ingredient.
- [ ] Bin behavior matches hand-first/plate-second rule.
- [ ] Sidebar checking consumes a snapshot, never your mutable storage.
- [ ] Correct serving clears only the checked plate and preserves hand contents.
- [ ] Incorrect serving preserves hand, plate and revision.
- [ ] Reset synchronizes with the other systems.

Your part is accepted when the entire collect/add/remove/discard sequence follows the table, all state tests pass, and snapshots can be checked by Member 3 without copying or modifying your internals.

---

## Shared plan — identical in all three guides

These are implementation instructions for a proposed repository structure, not a claim that these modules already exist. Build one working kitchen first. Cooking, stoves, cooked/raw states, walking customers, and additional levels are outside this milestone.

### What the first playable version does

The chef moves around the kitchen, collects one ingredient at a time, adds ingredients to a stationary plate, and serves that plate at a serving counter. Orders appear automatically in a sidebar. Serving means submitting the plate to the oldest active order. A correct submission consumes the plate contents and counts one completed order; an incorrect submission leaves everything unchanged.

Use these fixed rules until a reviewed change is agreed:
- Window: 1200 × 720. Kitchen: x=0–899. Sidebar: x=900–1199. World coordinates use pixels.
- Chef speed: 230 pixels/second. WASD and arrow keys move. Diagonal movement is normalized so it is not faster.
- E performs one nearby interaction per key press; holding E does not repeat. Q removes the most recently added ingredient at the plate station. Removal is allowed only when the chef's hand is empty and transfers that ingredient into the hand.
- One chef, one held ingredient, one stationary plate with capacity 4. No carried plate or inventory menu.
- Ingredient IDs: `sandwich`, `tomato`, `noodles`, `milk`. Boxes have unlimited stock. IDs are lowercase strings; display names and images are separate.
- Plate contents can contain repeated ingredients. Order matching uses ingredient counts and ignores insertion order. Missing ingredients, extra ingredients, and wrong quantities all fail.
- The bin discards the held ingredient. If the hand is empty, it clears the entire plate. No undo.
- Three active orders, each with 60 seconds of patience. Orders are automatically accepted when generated; there is no separate “take order” button.
- Recipe catalogue: pending team agreement for `sandwich`, `tomato`, `noodles`, and `milk`. These are collected items; no heating is required. Do not use the previous salad/sandwich/cheese-toast ingredient combinations.
- Start with three orders. On success or expiry, immediately replace that order with a new one at the end of the queue. Each order has a unique, increasing integer ID.
- Display accepted total, completed total, expired total, and score. Accepted includes every generated order, including the initial three and replacements. Each completion adds 100 points; expiry adds no points and no penalty.
- Timers use seconds from `delta_time`. Pausing freezes gameplay and timers. At zero or below an order expires before a queued serving action is processed that frame.
- Reject negative or non-finite time values with `ValueError`; zero is valid. Large time steps expire only orders present at the start of that update. Replacement orders start at 60 seconds.
- Invalid ingredient IDs raise `ValueError` at construction/API boundaries. Ordinary unsuccessful player actions return failure without raising an exception.

### Repository structure and ownership

```text
main.py                          Member 1: application entry point
requirements.txt                 Member 1: agreed, pinned dependencies
README.md                        Member 1: launch and setup instructions
.gitignore                       Member 1: local/generated exclusions
restaurant/
  __init__.py                    Member 1: package setup
  shared/
    __init__.py                  Member 1: package setup
    contracts.py                 Member 1: agreed data records only
    settings.py                  Member 1: window, layout, controls
  game_view.py                   Member 1: composition and event routing
  player/
    __init__.py                  Member 1
    controller.py                Member 1
    interaction.py               Member 1
  ingredients/
    __init__.py                  Member 2
    models.py                    Member 2: pure state
    system.py                    Member 2: ingredient actions
    renderer.py                  Member 2: boxes, hand, plate visuals
  orders/
    __init__.py                  Member 3
    models.py                    Member 3: pure order records
    system.py                    Member 3: timers, matching, counters
    sidebar.py                   Member 3: presentation
assets/
  player/                        Member 1
  ingredients/                   Member 2
  orders/                        Member 3
demos/
  player_demo.py                 Member 1
  ingredients_demo.py            Member 2
  orders_demo.py                 Member 3
tests/
  test_player.py                 Member 1
  test_ingredients.py            Member 2
  test_orders.py                 Member 3
  test_integration.py            Member 1; reviewed by all
docs/
  member_1_player.md
  member_2_ingredients_plate.md
  member_3_customer_orders.md
```

Ownership means who normally edits the file, not who may read it. Every member may read all code. Member 1 is the integration coordinator as well as the player developer. Member 2 and Member 3 request changes to shared files through Member 1 rather than silently editing them.

Use absolute imports such as `from restaurant.shared.contracts import PlateSnapshot`. Run commands from the repository root. Do not manipulate `sys.path` or depend on your personal working directory. Load assets relative to the package/repository location, not an absolute path on your laptop. Each demo must use colored placeholders if artwork is unavailable.

### Before independent work begins

Member 1 prepares a small `chore/shared-foundation` PR containing package folders, contracts, settings, dependency pins, launch instructions, and a minimal window. Member 2 and Member 3 review the API and rules. Merge it before starting feature branches. Empty package files are allowed; do not make fake implementations that pretend unfinished features work.

Use an existing agreed Python/Arcade environment if the repository already has one. Otherwise Member 1 verifies one Python/Arcade pair on all three computers and pins that exact Arcade version plus pytest in `requirements.txt`. Record the Python version in README. Do not independently upgrade packages. The version-sensitive drawing and collision APIs must follow the pinned release's documentation.

### Exact cross-system contracts

Implement these records in `restaurant/shared/contracts.py` as frozen dataclasses. Collection fields are tuples so callers cannot mutate another system's state. Python type hints do not validate values automatically; constructors or system boundaries must validate them.

```python
IngredientId = Literal["sandwich", "tomato", "noodles", "milk"]
TargetKind = Literal["box", "plate", "bin", "serve"]
Direction = Literal["up", "down", "left", "right"]

@dataclass(frozen=True)
class InteractionTarget:
    target_id: str
    kind: TargetKind
    x: float
    y: float
    ingredient_id: IngredientId | None = None

@dataclass(frozen=True)
class PlateSnapshot:
    ingredients: tuple[IngredientId, ...]
    revision: int

@dataclass(frozen=True)
class IngredientSnapshot:
    held: IngredientId | None
    plate: PlateSnapshot

@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str

@dataclass(frozen=True)
class OrderSnapshot:
    order_id: int
    recipe_name: str
    required: tuple[IngredientId, ...]
    remaining_seconds: float

@dataclass(frozen=True)
class OrderStats:
    accepted: int
    completed: int
    expired: int
    score: int

@dataclass(frozen=True)
class ServeResult:
    success: bool
    message: str
    order_id: int | None
    plate_revision: int
```

Import `Literal` from `typing` and `dataclass` from `dataclasses`. The snippets specify records, not full module implementations. Non-box targets have `ingredient_id=None`; box targets require a valid ingredient. IDs must be unique within the target collection.

**Member 1 exposes:**
```python
PlayerController(spawn: tuple[float, float])
PlayerController.set_move_key(key: str, pressed: bool) -> None
PlayerController.update(delta_time: float, walls: arcade.SpriteList) -> None
PlayerController.reset(spawn: tuple[float, float]) -> None
PlayerController.position -> tuple[float, float]  # read-only property
PlayerController.direction -> Direction         # read-only property
PlayerController.sprite -> arcade.Sprite       # rendering/collision access
choose_target(position, targets, radius=64.0) -> InteractionTarget | None
```

`set_move_key` accepts canonical `up/down/left/right` strings; GameView maps physical keys. GameView tracks physical keys so releasing W while Up is still held does not stop upward movement. `choose_target` uses Euclidean distance from chef center to interaction point, inclusive radius, and selects the nearest target; ties sort by `target_id`. Interaction does not require facing the target. Put interaction points on the reachable side of counters, separate from wall centers.

**Member 2 exposes:**
```python
IngredientSystem()
IngredientSystem.collect(ingredient_id: IngredientId) -> ActionResult
IngredientSystem.add_to_plate() -> ActionResult
IngredientSystem.remove_from_plate() -> ActionResult
IngredientSystem.discard() -> ActionResult
IngredientSystem.snapshot() -> IngredientSnapshot
IngredientSystem.clear_plate(expected_revision: int) -> bool
IngredientSystem.reset() -> None
```

Start with an empty hand and plate, revision 0. Every successful mutation of plate contents increments revision by one. Failed actions, collection, and discarding a held ingredient do not change plate revision. Clearing an already empty plate does not increment revision. `reset()` restores revision 0 and is used only when starting a new session.

`clear_plate` returns false with no mutation if revision differs; otherwise clears contents and returns true. This is a guard against consuming a different plate from the one checked. Only Member 2 mutates ingredient state.

**Member 3 exposes:**
```python
OrderSystem(seed: int | None = None)
OrderSystem.update(delta_time: float) -> None
OrderSystem.snapshot() -> tuple[OrderSnapshot, ...]
OrderSystem.stats() -> OrderStats
OrderSystem.try_serve(plate: PlateSnapshot) -> ServeResult
OrderSystem.reset(seed: int | None = None) -> None
OrderSidebar(bounds: tuple[int, int, int, int])
OrderSidebar.draw(orders: tuple[OrderSnapshot, ...], stats: OrderStats) -> None
```

Sidebar bounds are `(left, bottom, width, height)`. `OrderSystem` initializes three orders. It uses its own random generator so a supplied seed gives repeatable recipe sequences. Matching compares `Counter(plate.ingredients)` with `Counter(order.required)`. `try_serve` checks the oldest active order only. Success removes it, updates counters, generates one replacement, and returns its ID and the checked revision. Failure changes nothing, returns `order_id=None`, and echoes the checked revision. It never clears the plate itself.

### Integration wiring: one owner, one event loop

Only `main.py` starts the production Arcade window and event loop. Only GameView routes production keyboard events, updates systems, and coordinates serving. Demos have their own entry points and never launch on import.

GameView creates PlayerController, IngredientSystem, OrderSystem, renderer, sidebar, walls, and targets. Its behavior is:
1. Key press/release updates physical movement-key state. E/Q queue actions once per physical press; repeated key events while held are ignored.
2. On each unpaused update: move chef, advance orders, then process queued actions in arrival order. This ensures expired orders cannot be served.
3. E chooses a nearby target. Box → `collect(target.ingredient_id)`; plate → `add_to_plate()`; bin → `discard()`; serve → the sequence below. No target means a harmless “Move closer” message.
4. Q works only when the selected nearby target is the plate; call `remove_from_plate()`. Else show “Move to the plate”.
5. Serve captures `snapshot().plate`, calls `try_serve(plate)`, and on success immediately calls `clear_plate(result.plate_revision)`.
6. Those two serving calls run synchronously in the same update, with no intervening ingredient actions, callbacks, or awaits. A false clear after success is an integration defect: stop gameplay and report it, rather than retrying and awarding another order. The single event loop and immutable snapshot make this failure avoidable.
7. Draw reads snapshots only. Render kitchen/player/ingredient visuals, then sidebar and action feedback. Drawing never changes gameplay state.
8. Pause clears queued actions and movement state; gameplay presses while paused are ignored. On resume the player presses movement keys again. Reset clears input/action queues and resets all three systems together.

No player module imports ingredient/order internals. Ingredient and order models must run without importing Arcade or creating a window. Member 1 supplies feedback presentation in GameView; action messages from the other systems are displayed there. Renderers receive state rather than owning it.

### Git workflow for everyone

Use the same agreed remote repository. Work on your own clone and branch. Never commit directly to `main`; never force-push shared branches. Before creating a feature branch:
```shell
git switch main
git pull --ff-only origin main
git switch -c YOUR_BRANCH_NAME
```

Replace the placeholder with your guide's exact branch name. Set up a local environment:
```shell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Activation shown is for Windows Command Prompt; in PowerShell use `.\.venv\Scripts\Activate.ps1`. If activation is blocked, use `.\.venv\Scripts\python.exe` directly instead of changing machine security settings. README must state how to select the agreed Python interpreter.

Commit one meaningful piece at a time:
```shell
git status
git diff
git add PATHS_YOU_OWN
git commit -m "Describe the completed change"
git push -u origin YOUR_BRANCH_NAME
```

Replace placeholders with actual paths/branch. Stage only intended files. Do not commit `.venv/`, `__pycache__/`, `.pytest_cache/`, editor settings, secrets, local recordings, or generated build files. Member 1 puts exclusions in .gitignore.

When main changes, finish and commit your current work, then:
```shell
git fetch origin
git merge origin/main
```

If there is a conflict, inspect both versions. Do not click “accept ours” or “accept theirs” without understanding the effect. Coordinate with the file owner, preserve the agreed contract, and rerun checks. `git merge --abort` returns to the state before an unfinished merge when you need to regroup. Do not delete someone else's code to make a conflict disappear.

### Pull request and merge rules

Open a PR from your feature branch to main. Include: behavior delivered, owned files changed, API changes (normally none), commands run and results, manual demo evidence, known limitations, and dependencies on other PRs.

Require at least one other member's approval. Changes to shared contracts, settings, dependencies, or GameView that affect another system require that affected member's approval; contract changes need all three members to agree and all three guides to be updated together.

Member 1 merges approved PRs using the team's consistent merge method (squash merge is the default). Merge only after tests pass, the branch includes current main, requested changes are resolved, and the demo runs. If repository settings cannot enforce reviews, follow this rule manually. Delete the remote feature branch after merge; each person updates local main before starting another branch.

Suggested merge order: foundation → independent systems → integration. Members 2 and 3 can develop simultaneously after foundation; neither needs the other's implementation. Integration begins after public methods are available. A draft PR may be opened early for feedback.

### Shared checks before the milestone is complete

From the root:
```shell
python -m pytest tests
python -m compileall restaurant demos main.py
python main.py
```

Automated state tests do not require a graphical window. Graphical demos require a machine that can run Arcade and must be checked manually; do not hide a failed graphical check behind a skipped test. Every member runs their own demo and the integrated game after merge.

Member 1 owns `tests/test_integration.py`. All three review these checks:
- Correct plate completes exactly one order, adds 100 points, clears plate once, keeps held ingredient unchanged, and leaves three active orders.
- Wrong plate leaves plate, queue, score, and counters unchanged.
- An order reaching zero expires before a same-frame serving action; only a remaining/new order can be served.
- Simultaneous expiries replace every expired order once, with unique IDs and fresh timers.
- Pause freezes movement/timers/actions. Reset restores empty hand/plate, three orders, score 0, completed/expired 0, accepted 3.
- A chef cannot enter the sidebar or pass through kitchen walls; unreachable objects cannot be used.
- Repeated E presses cannot complete the same order twice.

### Common “do not edit” rules

Do not edit another member's owned modules, demos, tests, or assets without coordination and explicit assignment. Do not change a public method name, ingredient ID, control, or result record independently. Do not put all code in main.py, duplicate another system's state, start a window during import, add circular imports, or add cooking. Do not format the entire repository in a feature PR. Keep changes focused.

If the actual repository already uses different names, Member 1 maps existing paths to these responsibilities in a single reviewed foundation PR; do not create duplicate systems beside working code.

### Arcade reference

Use the documentation for the pinned version. Arcade's input callbacks and update loop support this separation of input, state updates, and drawing. See [official Window/View documentation](https://api.arcade.academy/en/stable/api_docs/api/window.html) and [official movement/collision tutorial](https://api.arcade.academy/en/stable/tutorials/platform_tutorial/step_04.html). Our game rules and interfaces above are team design decisions, not requirements imposed by Arcade.
