# Restaurant game — shared team starter

One shared Python Arcade project for all three members. The Classic Chef player
system is working now. Ingredients/plates and customer/orders have reserved
folders and shared data definitions, ready for the other members to implement.

The tiled kitchen uses one consistent low top-down view across the entire room,
with supplied prop images, a service hatch into the dining room and a chopping-board
table. The chef is enlarged to suit the furniture. Its compact 960 x 704 world and
256-pixel sidebar fit inside a comfortable, resizable window that accounts for
Windows display scaling and the taskbar. Food/cutting stay preview-only.
See [kitchen layout notes](docs/kitchen_layout.md).

## Play without the repository

Download **kitchen-demo-windows-v0.4.0.zip** from the
[polished restaurant demo release](https://github.com/toocoolqi/imaging_and-_special-effects/releases/tag/kitchen-demo-v0.4.0).
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
| E | Interact once with the nearest station within 64 pixels |
| Q | Plate-removal intent (feedback only for now) |
| P | Pause/resume |
| R | Reset |
| F1 | Show collision and interaction guides |
| Esc | Exit |
| Drag window edges / maximize | Resize while keeping the whole room visible |

No hold-item animations are included. The current stations report interactions;
they do not collect food, assemble plates, serve orders or award points yet.
The chopping table's E preview is reserved for the future cutting system.

## Each member's starting point

| Member | Main files to work in | Read first |
| --- | --- | --- |
| 1 — Player/integration | `restaurant/player/`, `restaurant/game_view.py` | [Player guide](docs/member_1_player.md), [working interface](docs/player_integration.md) |
| 2 — Ingredient + plate | `restaurant/ingredients/`, `assets/ingredients/` | [Member 2 guide](docs/member_2_ingredients_plate.md) |
| 3 — Customer / order | `restaurant/orders/`, `assets/orders/` | [Member 3 guide](docs/member_3_customer_orders.md) |

All members use `restaurant/shared/contracts.py` and `settings.py`. The immutable
records are already defined there. Coordinate shared changes before editing;
never create a second copy of another member's state or contracts.

Room furniture, solids and station approach points live together in
`restaurant/kitchen/layout.py`; artwork rendering lives in `scene.py`. The
new `chop` target kind adds a cutting-system hook without changing food IDs.

Member 2 starts with `models.py` and `system.py`, then adds `renderer.py`,
`demos/ingredients_demo.py`, and `tests/test_ingredients.py`.
Member 3 starts with `models.py` and `system.py`, then adds `sidebar.py`,
`demos/orders_demo.py`, and `tests/test_orders.py`.
Their package folders currently contain guidance only, not pretend implementations.

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
