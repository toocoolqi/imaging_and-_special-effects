> The assignment build has a clickable main menu, consistent pixel rendering, four playable days in four kitchen art sets (overgrown, warm, damaged steel, steel), Task 2 cooking, timed orders with gold and speed tips that get busier each day, order effects, room ambience and music, and a larger chef with standing, walking, plate carrying and chopping animations. See [the current controls and gameplay](docs/FINAL_GAMEPLAY.md) and [the orders and kitchens guide](docs/GUIDE_orders_and_kitchens.md).

# Restaurant game — shared team starter

One shared Python Arcade project for all three members. The Classic Chef player
and task2 ingredient/plate systems now work together. The current division of
work, including both kitchens and the next food/order milestone, is in
[TEAM_PLAN.md](docs/TEAM_PLAN.md).

The tiled kitchen uses one consistent low top-down view across the entire room,
with supplied prop images, a service hatch into the dining room and a chopping-board
table. The chef is enlarged to suit the furniture. Its compact 960 x 704 world and
256-pixel sidebar fit inside a comfortable, resizable window that accounts for
Windows display scaling and the taskbar. Task2 pickup, plating, removal and discarding now work.
See [kitchen layout notes](docs/kitchen_layout.md).

## Play without the repository

Download **kitchen-demo-windows-v0.8.1.zip** from the
[current release](https://github.com/toocoolqi/imaging_and-_special-effects/releases/tag/kitchen-demo-v0.8.1).
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
| Click Play / Enter on the menu | Start the first kitchen |
| Click Quit / Esc on the menu | Close the app |
| WASD / arrows | Move, with equal straight and diagonal speed |
| E | Use the nearest station once within 64 pixels |
| E at the service hatch | Serve the carried plate, or a sandwich or milk in hand |
| Q | Remove the newest plated food into empty hands |
| Enter | Advance after reaching the day's gold target and returning the plate |
| 1 - 4 | Jump to a day (starts it fresh) |
| M | Mute/unmute |
| P | Pause/resume |
| R | Reset |
| F1 | Show collision and interaction guides |
| Esc | Exit |
| Drag window edges / maximize | Resize while keeping the whole room visible |

Press E at the board with a tomato in hand or on the carried plate. The chef
chops it, then you can press E to collect the pieces.

The artwork shares one pixel grid, with sharp enlargement and separately drawn
text. The stove, sink and service hatch are fixed to the back wall; the chef can
use their fronts but cannot walk into their rear gaps. Held food follows the
moving hand. See [rendering and integration notes](docs/VISUAL_POLISH.md).

## Current member assignments

Read [TEAM_PLAN.md](docs/TEAM_PLAN.md), then your guide:

| Role | Current responsibility | Guide |
| --- | --- | --- |
| Member 1 | Player, maps, integration and packaging | [Player/integration](docs/team/01_player_integration.md) |
| Member 2 / task2 | Food, plates, pots, sidebar orders, serving and sound | [Food/orders](docs/team/02_food_cooking_orders.md) |
| Member 3 | Both kitchens and their overgrown/damaged variants | [Environments](docs/team/03_kitchen_environments.md) |

The old member guides describe the previous split and are historical. The
IngredientSystem from task2 now works in the kitchen; run its independent lab
with `python -m demos.ingredients_demo`; the order system has its own lab,
`python -m demos.orders_demo`. The main game uses the contributed Task 2
cooking from commit `4479a22` with the timed order system and the four
kitchen art sets described in [the orders and kitchens guide](docs/GUIDE_orders_and_kitchens.md).

Generated assets are reproducible:

```powershell
.venv\Scripts\python.exe -m tools.build_kitchens   # four kitchen art sets
.venv\Scripts\python.exe -m tools.make_sounds      # order cues, ambience and music
```

## Run the checks

```powershell
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m compileall -q restaurant demos tools main.py
```

Tests include a real hidden Arcade window, so run the full suite on a desktop.
The source suite covers movement, collisions, animation, input, interactions and
shared records. Test the controls visually on your own computer before a PR.

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

Read [CONTRIBUTING.md](CONTRIBUTING.md) before your first commit. The original
member guides describe the eventual integrated game; this repository currently
delivers its shared foundation and player subsystem.
