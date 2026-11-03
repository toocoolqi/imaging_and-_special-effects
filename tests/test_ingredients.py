"""Member 2 gameplay rules, exercised without an Arcade window."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import subprocess
import sys

import pytest

from restaurant.ingredients import IngredientSystem
from restaurant.shared.contracts import ActionResult, IngredientSnapshot, PlateSnapshot


def fill_plate(system, ingredients):
    for ingredient in ingredients:
        assert system.collect(ingredient).success
        assert system.add_to_plate().success


def test_initial_state_and_fresh_snapshots():
    system = IngredientSystem()
    first = system.snapshot()
    second = system.snapshot()
    assert first == IngredientSnapshot(None, PlateSnapshot((), 0))
    assert first is not second
    assert first.plate is not second.plate


@pytest.mark.parametrize("ingredient", ["sandwich", "tomato", "noodles", "milk"])
def test_collect_each_ingredient(ingredient):
    system = IngredientSystem()
    assert system.collect(ingredient) == ActionResult(True, f"Collected {ingredient}")
    assert system.snapshot() == IngredientSnapshot(ingredient, PlateSnapshot((), 0))


@pytest.mark.parametrize("held", [None, "noodles"])
@pytest.mark.parametrize("invalid", ["pizza", "lettuce", "bread", "cheese", "Tomato", "", None, 42, ["noodles"]])
def test_invalid_collection_raises_even_with_full_hand(held, invalid):
    system = IngredientSystem()
    if held is not None:
        system.collect(held)
    before = system.snapshot()
    with pytest.raises(ValueError):
        system.collect(invalid)
    assert system.snapshot() == before


def test_second_collection_preserves_hand_and_plate():
    system = IngredientSystem()
    fill_plate(system, ("sandwich",))
    system.collect("tomato")
    before = system.snapshot()
    assert system.collect("milk") == ActionResult(False, "Hand is full")
    assert system.snapshot() == before


def test_add_transfers_hand_and_increments_revision_once():
    system = IngredientSystem()
    system.collect("tomato")
    assert system.add_to_plate() == ActionResult(True, "Added tomato")
    assert system.snapshot() == IngredientSnapshot(None, PlateSnapshot(("tomato",), 1))
    before = system.snapshot()
    assert system.add_to_plate() == ActionResult(False, "Hand is empty")
    assert system.snapshot() == before


def test_duplicates_allowed_and_fifth_add_preserves_held_food():
    system = IngredientSystem()
    fill_plate(system, ("noodles",) * 4)
    assert system.snapshot().plate == PlateSnapshot(("noodles",) * 4, 4)
    system.collect("milk")
    before = system.snapshot()
    assert system.add_to_plate() == ActionResult(False, "Plate is full")
    assert system.snapshot() == before


def test_remove_is_last_in_first_out_and_full_hand_blocks_it():
    system = IngredientSystem()
    fill_plate(system, ("sandwich", "tomato", "milk"))
    assert system.remove_from_plate() == ActionResult(True, "Removed milk")
    assert system.snapshot() == IngredientSnapshot(
        "milk", PlateSnapshot(("sandwich", "tomato"), 4),
    )
    before = system.snapshot()
    assert system.remove_from_plate() == ActionResult(False, "Hand is full")
    assert system.snapshot() == before
    system.discard()
    assert system.remove_from_plate().success
    assert system.snapshot() == IngredientSnapshot("tomato", PlateSnapshot(("sandwich",), 5))
    system.discard()
    assert system.remove_from_plate().success
    assert system.snapshot() == IngredientSnapshot("sandwich", PlateSnapshot((), 6))


def test_empty_plate_removal_changes_nothing():
    system = IngredientSystem()
    before = system.snapshot()
    assert system.remove_from_plate() == ActionResult(False, "Plate is empty")
    assert system.snapshot() == before


def test_discard_prioritizes_hand_then_clears_plate_once():
    system = IngredientSystem()
    fill_plate(system, ("noodles", "milk"))
    system.collect("tomato")
    assert system.discard() == ActionResult(True, "Discarded tomato")
    assert system.snapshot() == IngredientSnapshot(None, PlateSnapshot(("noodles", "milk"), 2))
    assert system.discard() == ActionResult(True, "Plate cleared")
    assert system.snapshot() == IngredientSnapshot(None, PlateSnapshot((), 3))
    assert system.discard() == ActionResult(False, "Nothing to discard")
    assert system.snapshot().plate == PlateSnapshot((), 3)


def test_snapshot_is_immutable_and_survives_actions_and_reset():
    system = IngredientSystem()
    fill_plate(system, ("noodles",))
    system.collect("milk")
    saved = system.snapshot()
    with pytest.raises(FrozenInstanceError):
        saved.held = "tomato"
    with pytest.raises(FrozenInstanceError):
        saved.plate.revision = 99
    with pytest.raises(TypeError):
        saved.plate.ingredients[0] = "tomato"
    system.add_to_plate()
    system.discard()
    system.reset()
    assert saved == IngredientSnapshot("milk", PlateSnapshot(("noodles",), 1))


def test_matching_clear_preserves_hand_and_rejects_repeated_consumption():
    system = IngredientSystem()
    fill_plate(system, ("noodles", "milk"))
    checked = system.snapshot().plate
    system.collect("tomato")
    assert system.clear_plate(checked.revision) is True
    assert system.snapshot() == IngredientSnapshot("tomato", PlateSnapshot((), 3))
    before = system.snapshot()
    assert system.clear_plate(checked.revision) is False
    assert system.snapshot() == before


def test_stale_clear_preserves_plate_and_hand():
    system = IngredientSystem()
    fill_plate(system, ("noodles",))
    checked = system.snapshot().plate
    fill_plate(system, ("milk",))
    system.collect("sandwich")
    before = system.snapshot()
    assert system.clear_plate(checked.revision) is False
    assert system.snapshot() == before


def test_empty_clear_requires_matching_revision_and_never_increments():
    system = IngredientSystem()
    assert system.clear_plate(0) is True
    system.collect("noodles")
    system.add_to_plate()
    system.remove_from_plate()
    before = system.snapshot()
    assert system.clear_plate(0) is False
    assert system.clear_plate(2) is True
    assert system.snapshot() == before


def test_reset_restores_initial_state_and_allows_new_session():
    system = IngredientSystem()
    fill_plate(system, ("noodles", "milk"))
    system.collect("tomato")
    assert system.reset() is None
    assert system.snapshot() == IngredientSnapshot(None, PlateSnapshot((), 0))
    fill_plate(system, ("sandwich",))
    assert system.snapshot().plate == PlateSnapshot(("sandwich",), 1)


def test_system_instances_do_not_share_storage():
    first = IngredientSystem()
    second = IngredientSystem()
    fill_plate(first, ("tomato",))
    assert second.snapshot() == IngredientSnapshot(None, PlateSnapshot((), 0))


def test_import_and_actions_work_when_arcade_import_is_blocked():
    script = """
import sys
class BlockArcade:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'arcade' or fullname.startswith('arcade.'):
            raise AssertionError('State logic must not import Arcade')
sys.meta_path.insert(0, BlockArcade())
from restaurant.ingredients import IngredientSystem
system = IngredientSystem()
assert system.collect('tomato').success
assert system.add_to_plate().success
assert system.snapshot().plate.ingredients == ('tomato',)
assert 'arcade' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
