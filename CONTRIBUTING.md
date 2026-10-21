# Working together

All three members clone the same private repository. Each clone contains the
same project. Do not make separate GitHub repositories for the three systems.

## Start a task

Save/commit any current work first, then update main and create your branch:

```shell
git switch main
git pull --ff-only origin main
git switch -c feature/member-2-ingredients-plate
```

Use `feature/member-1-player`, `feature/member-2-ingredients-plate`, or
`feature/member-3-customer-orders` as appropriate. If your branch already exists,
use `git switch BRANCH_NAME` instead of creating it again.

## Files and ownership

- Member 1: player code/assets, `restaurant/kitchen/`, and the main game view.
  Coordinates shared files; kitchen placement notes are in `docs/kitchen_layout.md`.
- Member 2: ingredients/plate code, assets, independent demo and tests.
- Member 3: orders/sidebar code, assets, independent demo and tests.
- Shared: `restaurant/shared/`, dependencies, launch/build files and README.
  Discuss interface changes with affected members before making them.

Do not modify another member's system just to make your code fit. Use the shared
records and documented methods. Player code must remain independent of ingredient
and order implementations. Never add duplicate held-item or plate state to it.

## Save and submit

Run your tests and demo, then inspect and stage only the intended files:

```shell
git status
git diff
git add restaurant/ingredients demos/ingredients_demo.py tests/test_ingredients.py
git commit -m "Add ingredient collection and plate state"
git push -u origin feature/member-2-ingredients-plate
```

The example paths are for Member 2 after those files have been created. Substitute
your own actual files. Open a pull request into main. Describe the behavior,
interface changes, tests and remaining work. Ask another member to review it.
Never commit `.venv`, caches, generated applications, passwords or personal data.

## Integrate

Merge the shared foundation first. Members 2 and 3 can then develop independently.
Member 1 connects their public APIs through `GameView.handle_interaction`, adds
renderers, and tests the collect → plate → serve sequence together with them.
No hold-item animation is required for this milestone.

To bring new main changes into your branch, first commit your current work:

```shell
git fetch origin
git merge origin/main
```

Resolve conflicts with the file owner, preserve both intended changes, and rerun
tests. Do not force-push shared branches. After a reviewed merge, everyone updates
their local main before starting new work.

## Repository owner setup

Keep the GitHub repository private. Invite your two teammates with write access
using their actual GitHub usernames. Their names are not known in this starter,
so no invitations or CODEOWNERS assignments have been invented. Enable PR review
requirements for main if your GitHub plan supports them; otherwise follow the
same review rule manually. Source control does not replace communication about
shared interfaces.
