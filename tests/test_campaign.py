"""Exercise all four days through the same key events used by a player."""
import arcade
import pytest

from restaurant.game_view import create_window
from restaurant.ingredients.chopping import CHOP_SECONDS
from restaurant.shared.contracts import PlateLocation, PotStage


@pytest.fixture(autouse=True)
def fixed_order_arrival(monkeypatch):
    monkeypatch.setattr("restaurant.orders.system.Random.uniform", lambda self, low, high: 8.0)


def use(view, target_id):
    target = next(target for target in view.targets if target.target_id == target_id)
    view.player.reset((target.x, target.y))
    assert not arcade.check_for_collision_with_list(view.player.sprite, view.walls)
    press(view, arcade.key.E)


def press(view, key):
    view.on_key_press(key, 0)
    view.on_update(0)
    view.on_key_release(key, 0)


def oldest_order(view):
    while not view.orders.snapshot():            # a short gap between customers
        view.on_update(0.5)
    return view.orders.snapshot()[0]


def chop_tomato_onto_plate(view, seen):
    """Chop a tomato from the carried plate, checking the pose and pause."""
    use(view, "box_tomato")
    use(view, "chopping_board")
    view.on_update(CHOP_SECONDS / 2)
    view.on_draw()
    assert view.chopping.state == "chopping"
    assert "tomato" not in view.ingredients.snapshot().plate.ingredients
    old_position = view.player.position
    view.on_key_press(arcade.key.S, 0)
    view.on_update(CHOP_SECONDS / 4)
    view.on_key_release(arcade.key.S, 0)
    assert view.player.position == old_position
    progress = view.chopping.progress
    press(view, arcade.key.P)
    view.on_update(5)
    assert view.chopping.progress == progress
    press(view, arcade.key.P)
    view.on_update(CHOP_SECONDS)
    assert view.chopping.state == "ready"
    use(view, "chopping_board")
    assert "chopped_tomato" in view.ingredients.snapshot().plate.ingredients
    seen.add("chopping")


def cook_pasta_onto_plate(view, seen):
    """Load the pot from the carried plate, check pause, collect the pasta."""
    for food in ("noodles", "milk", "tomato"):
        use(view, f"box_{food}")
    use(view, "pot")
    assert view.ingredients.snapshot().pot.stage is PotStage.COOKING
    press(view, arcade.key.P)
    view.on_update(5)
    assert view.ingredients.snapshot().pot.remaining_seconds == 4
    press(view, arcade.key.P)
    view.on_update(4)
    assert view.ingredients.snapshot().pot.stage is PotStage.READY
    use(view, "pot")
    assert view.ingredients.snapshot().plate.ingredients == ("pasta",)
    seen.add("cooking")


def serve_one_order(view, seen):
    order = oldest_order(view)                   # live from arrival: no ticket to take
    score = view.orders.stats().score
    state = view.ingredients.snapshot()
    if order.recipe_name in ("Sandwich", "Milk"):
        if state.plate.location is PlateLocation.CARRIED:
            use(view, "plate")                   # hands must be free
        use(view, f"box_{order.required[0]}")
        seen.add("by_hand")
    else:
        if state.plate.location is not PlateLocation.CARRIED:
            use(view, "plate")
        assert view.ingredients.snapshot().plate.ingredients == ()
        if order.required == ("pasta",):
            cook_pasta_onto_plate(view, seen)
        else:
            for food in order.required:
                if food == "tomato":
                    chop_tomato_onto_plate(view, seen)
                else:
                    use(view, f"box_{food}")
    use(view, "serve")
    assert view.orders.stats().score > score
    assert view.ingredients.snapshot().held is None
    if view.ingredients.snapshot().plate.location is PlateLocation.CARRIED:
        assert view.ingredients.snapshot().plate.ingredients == ()   # the same plate comes back
    paid, completed = view.orders.stats().score, view.orders.stats().completed
    if not view.day_complete:
        use(view, "serve")                       # a second press cannot be paid twice
        assert view.orders.stats().score == paid
        assert view.orders.stats().completed == completed


def complete_day(view, seen, *, check_rejection=False):
    if check_rejection:
        use(view, "serve")                       # empty hands: nothing to serve
        assert "Bring a plate" in view.message
        use(view, "plate")
        use(view, "box_noodles")
        before = view.ingredients.snapshot(), view.orders.stats().score
        use(view, "serve")                       # nobody ordered plain noodles
        assert (view.ingredients.snapshot(), view.orders.stats().score) == before
        assert "sent it back" in view.message
        use(view, "bin")
    guard = 0
    while not view.day_complete:
        guard += 1
        assert guard < 20, "a day should finish within a few orders"
        serve_one_order(view, seen)
    gold = view.orders.stats().score
    assert gold >= view.day.rules.target_gold
    if view.ingredients.snapshot().plate.location is not PlateLocation.CARRIED:
        use(view, "plate")
    press(view, arcade.key.ENTER)                # refused while carrying the plate
    assert view.ingredients.snapshot().plate.location is PlateLocation.CARRIED
    assert "Return" in view.message
    use(view, "plate")
    assert view.ingredients.snapshot().plate.location is PlateLocation.DOCKED
    return gold


def test_four_day_playthrough_and_restart():
    window = create_window(visible=False, seed=4)
    try:
        view = window.current_view
        seen, earned = set(), 0
        for day in range(4):
            assert view.day_index == day
            earned += complete_day(view, seen, check_rejection=(day == 0))
            view.on_draw()
            press(view, arcade.key.ENTER)
        assert view.finished
        assert view.total_gold == earned
        assert seen == {"chopping", "cooking", "by_hand"}
        view.on_draw()
        press(view, arcade.key.R)
        assert view.day_index == view.total_gold == 0
        assert not view.finished
    finally:
        window.close()


def test_expired_ticket_preserves_plate_and_keeps_newer_orders():
    window = create_window(visible=False)
    try:
        view = window.current_view
        use(view, "box_sandwich")
        use(view, "plate")
        old = view.orders.snapshot()[0]
        view.on_update(121)                      # longer than Day 1's 90-second timer
        assert view.orders.stats().expired >= 1
        assert all(order.order_id > old.order_id for order in view.orders.snapshot())
        assert view.ingredients.snapshot().plate.ingredients == ("sandwich",)
    finally:
        window.close()
