# Restaurant game — shared team starter

One shared Python Arcade project for all three members. The Classic Chef player,
food preparation, cooking, plate transport, and service orders work together in
the warm kitchen. The current division of
work, including both kitchens and the next food/order milestone, is in
[TEAM_PLAN.md](docs/TEAM_PLAN.md).

The tiled kitchen uses one consistent low top-down view across the entire room,
with supplied prop images, a service hatch into the dining room and a chopping-board
table. The chef is enlarged to suit the furniture. Its compact 960 x 704 world and
256-pixel sidebar fit inside a comfortable, resizable window that accounts for
Windows display scaling and the taskbar. Task2 pickup, plating, removal and discarding now work.
See [kitchen layout notes](docs/kitchen_layout.md).

## Play without the repository

Download **kitchen-demo-windows-v0.5.0.zip** from the
[polished restaurant demo release](https://github.com/toocoolqi/imaging_and-_special-effects/releases/tag/kitchen-demo-v0.5.0).
Extract the whole ZIP and
double-click `PlayerDemo/PlayerDemo.exe`. It includes Python, Arcade and artwork.
Keep `_internal` beside the EXE. No Git or Python installation is needed to play.
The portable demo is Windows 64-bit; the source below can be developed separately.

The downloadable app is a snapshot of the completed player demo. Editing this
repository does not change that EXE; rebuild it when you want a new app version.

## Start developing

The private team repository is
`https://github.com/toocoolqi/imaging_and-_special-effects.git`.
Each teammate needs repository access from its owner and Python 3.12 installed.
Each member starts by cloning the same repository:

```powershell
git clone https://github.com/toocoolqi/imaging_and-_special-effects.git
cd imaging_and-_special-effects
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

If you already have this folder locally, open a terminal here and start at the
`py -3.12` line. Activation is not required. For macOS/Linux use
`python3.12 -m venv .venv` and `.venv/bin/python` instead.

Tested development environment: Python 3.12.14, Arcade 3.3.3, Windows. All rendering
and input use Arcade. A graphics driver supporting OpenGL 3.3+ is required.

## Controls

| Key | Action |
| --- | --- |
| WASD / arrows | Move, with equal straight and diagonal speed |
| E | Use the nearest station once within 64 pixels |
| Q | Remove the newest plated food into empty hands |
| P | Pause/resume |
| R | Reset |
| M | Mute/unmute kitchen sounds |
| F1 | Show collision and interaction guides |
| Esc | Exit |
| Drag window edges / maximize | Resize while keeping the whole room visible |

Use E at the service table to start the round with one order. A new order
arrives after a random wait of 5 to 10 seconds while there is room, up to three active orders.
Each order has two minutes from when it appears. A successful
serve earns 100 points, plus 50 when served within 30 seconds of the order starting.
Pick up the plate with
E at its table, then use E at pantry crates to add food directly to the plate.
Without the plate, carry one item by hand and use E at the table to add it.
For Pasta, collect noodles, milk, and tomato on the plate, then use E at the
stove to transfer the recipe ingredients. After four seconds, use E at the
stove again with an empty plate to collect the cooked portion. Pasta takes up
the whole plate. Use E at the bin while carrying the plate to empty it.
Use E at the hatch to
serve, then E at the plate table to return the empty plate. A plain Sandwich
or Milk order can also be served directly from your hand.
The chopping board remains a preview station.

## Current member assignments

Read [TEAM_PLAN.md](docs/TEAM_PLAN.md), then your guide:

| Role | Current responsibility | Guide |
| --- | --- | --- |
| Member 1 | Player, maps, integration and packaging | [Player/integration](docs/team/01_player_integration.md) |
| Member 2 / task2 | Food, plates, pots, sidebar orders, serving and sound | [Food/orders](docs/team/02_food_cooking_orders.md) |
| Member 3 | Both kitchens and their overgrown/damaged variants | [Environments](docs/team/03_kitchen_environments.md) |

The old member guides describe the previous split and are historical. The
IngredientSystem also runs independently with `python -m demos.ingredients_demo`.
Run the main game for cooking, plate transport, order service, and audio.

## Run the checks

```powershell
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m compileall -q restaurant demos tools main.py
.venv\Scripts\python.exe main.py --self-test artifacts\food-check
```

Tests include a real hidden Arcade window, so run the full suite on a desktop.
The self-test cooks and serves two consecutive orders and saves screenshots
of cooking, serving, and returning the plate.

## Package a new independent Windows demo

From this repository on Windows:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe -m PyInstaller --noconfirm PlayerDemo.spec
dist\PlayerDemo\PlayerDemo.exe
```

Share the **whole** `dist/PlayerDemo` folder as a ZIP. For a packaged check:

```powershell
dist\PlayerDemo\PlayerDemo.exe --self-test artifacts\packaged-check
```

The report is `artifacts/packaged-check/self-test.json`; success means
`"passed": true`. Keep generated apps, environments and caches out of Git.
The build-only hook corrects Arcade 3.3.3's VERSION-file packaging destination.
See [PyInstaller's runtime resource guidance](https://pyinstaller.org/en/stable/runtime-information.html).

Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first commit.
