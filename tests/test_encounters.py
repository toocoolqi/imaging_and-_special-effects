"""Inventory safety, traversable detours, warning time and vampire sweep rules."""
import pytest

from restaurant.hazards.navigation import BLOCKER_SIZE, CANDIDATES, routes_open, safe_blocker_position
from restaurant.hazards.system import Blocker, Encounters, Ghost, Vampire
from restaurant.ingredients import IngredientSystem
from restaurant.kitchen.days import DAYS
from restaurant.shared.contracts import PlateLocation


def encounter(day_index=0):
    day = DAYS[day_index]
    plate = next(p for p in day.props if p.prop_id == "display_plate")
    return Encounters(day_index, day.walls, [(t.x, t.y - 32) for t in day.targets], (plate.x, plate.y - 62))


def plated(*items):
    food = IngredientSystem()
    for item in items:
        food.collect(item)
        food.add_to_plate()
    return food


def test_ghost_takes_only_docked_food_and_invalidates_old_revision():
    food = plated("tomato", "sandwich")
    before = food.snapshot()
    food.pickup_plate()
    assert food.steal_docked_food() == ()
    food.return_plate()
    food.collect("milk")
    assert food.steal_docked_food() == ("tomato", "sandwich")
    after = food.snapshot()
    assert after.held == "milk" and after.plate.location is PlateLocation.DOCKED
    assert after.plate.ingredients == () and after.plate.revision > before.plate.revision
    assert not food.clear_plate(before.plate.revision)
    assert food.steal_docked_food() == ()


def test_recovery_is_atomic_when_new_food_fills_the_plate():
    food = plated("tomato", "sandwich")
    payload = food.steal_docked_food()
    for _ in range(3):
        food.collect("milk")
        food.add_to_plate()
    before = food.snapshot()
    assert not food.restore_stolen_food(payload).success
    assert food.snapshot() == before
    food.discard()
    food.pickup_plate()
    assert food.restore_stolen_food(payload).success
    assert food.snapshot().plate.ingredients == payload
    assert food.snapshot().plate.location is PlateLocation.CARRIED


def test_recovered_pasta_cannot_mix_with_raw_food():
    food = plated("tomato")
    before = food.snapshot()
    assert not food.restore_stolen_food(("pasta",)).success
    assert food.snapshot() == before
    food.discard()
    assert food.restore_stolen_food(("pasta",)).success
    assert not food.restore_stolen_food(("milk",)).success
    with pytest.raises(ValueError):
        food.restore_stolen_food(("invalid",))


def test_two_misses_warn_then_steal_reclaim_once_without_touching_hand():
    game, food = encounter(), plated("sandwich", "tomato")
    player = (480, 188)
    game.missed_order()
    game.update(.1, food, player)
    assert game.ghost is None
    game.missed_order()
    game.update(.1, food, player)
    assert game.ghost.state == "warning"
    assert food.snapshot().plate.ingredients == ("sandwich", "tomato")
    game.update(1, food, player)
    assert game.ghost.state == "warning"
    for _ in range(120):
        game.update(.05, food, player)
        if game.ghost and game.ghost.food:
            break
    g = game.ghost
    assert g.food == ("sandwich", "tomato")
    assert food.snapshot().plate.ingredients == ()
    assert game.reclaim(food, (50, 50)) is None
    assert game.reclaim(food, (g.x, g.y)).success
    assert game.ghost is None and game.reclaim(food, (g.x, g.y)) is None
    assert food.snapshot().plate.ingredients == ("sandwich", "tomato")
    assert "ghost_recover" in [cue for cue, _ in game.drain_events()]


def test_escaped_ghost_takes_food_but_never_the_plate():
    game, food = encounter(), plated("milk")
    payload = food.steal_docked_food()
    game.ghost = Ghost(1030, 319, "flee", 0, payload)
    game.update(.1, food, (50, 50))
    assert game.ghost is None
    assert food.snapshot().plate.ingredients == ()
    assert food.snapshot().plate.location is PlateLocation.DOCKED
    assert "escaped" in game.drain_events()[0][1]


@pytest.mark.parametrize("day_index", range(4))
def test_blocker_leaves_all_stations_and_chopping_work_position_reachable(day_index):
    day = DAYS[day_index]
    stations = [(t.x, t.y - 32) for t in day.targets]
    stations += [(t.x - 41, t.y - 18) for t in day.targets if t.kind == "chop"]
    player = (day.spawn[0], day.spawn[1] - 32)
    point = safe_blocker_position(day.walls, stations, player)
    assert point is not None
    assert routes_open(day.walls, stations, player, (*point, *BLOCKER_SIZE))
    assert not routes_open(day.walls, stations, player, (480, 220, 960, 60))


@pytest.mark.parametrize("day_index,limit", [(0, 0), (1, 0), (2, 1), (3, 2)])
def test_blocker_frequency_is_capped_by_day(day_index, limit):
    game, food = encounter(day_index), IngredientSystem()
    game.misses = 20
    for _ in range(130):
        game.update(.5, food, (480, 188))
    assert game.blocker_count == limit


def test_blocker_cancels_if_chef_walks_into_the_warning_marker():
    game, food = encounter(2), IngredientSystem()
    game.misses = 2
    game.update(.01, food, (480, 188))
    point = (game.blocker.x, game.blocker.y)
    game.update(2.1, food, point)
    assert game.blocker is None and game.blocker_rectangle is None
    assert game.blocker_count == 0


def test_vampire_warns_then_hits_once_and_clears_stun():
    game, food = encounter(1), IngredientSystem()
    game.next_vampire = 0
    player = (150, 210)
    game.update(.01, food, player)
    assert game.vampire.state == "warning" and game.stun == 0
    game.update(1.8, food, player)
    assert game.vampire.state == "warning" and game.stun == 0
    for _ in range(30):
        game.update(.05, food, player)
        if game.stun:
            break
    assert game.stun > 0 and game.vampire.hit
    game.update(.9, food, player)
    assert game.stun == 0
    assert [cue for cue, _ in game.drain_events()].count("vampire_bite") == 1


def test_vampire_can_be_dodged_and_cannot_tunnel_over_stationary_chef():
    game, food = encounter(1), IngredientSystem()
    game.vampire = Vampire(20, 210, 1, "sweep", 0)
    game.update(.5, food, (120, 245))
    assert not game.vampire.hit and game.stun == 0
    game.vampire = Vampire(20, 210, 1, "sweep", 0)
    game.update(.5, food, (120, 210))
    assert game.vampire.hit and game.stun > 0


def test_day_one_never_spawns_vampires_and_invalid_time_is_rejected():
    game, food = encounter(), IngredientSystem()
    game.update(180, food, (480, 188))
    assert game.vampire is None
    for value in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            game.update(value, food, (480, 188))
