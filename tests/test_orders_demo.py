"""Hidden-window checks for the order demo, the sidebar and the effects."""
import arcade
import pytest

from demos.orders_demo import PANEL, RULES, OrdersDemo, create_window
from restaurant.orders import OrderSystem
from restaurant.orders.effects import OrderEffects
from restaurant.orders.sidebar import (
    GHOST_SECONDS, OrderSidebar, blink_on, greyscale_texture, timer_color,
)
from restaurant.shared.contracts import OrderEvent, OrderSnapshot, OrderStats


@pytest.fixture(scope="module")
def window():
    window = create_window(visible=False)
    yield window
    window.close()


@pytest.fixture
def view(window):
    view = OrdersDemo(sound=False, seed=7)
    window.show_view(view)
    return view


def press(view, key):
    view.on_key_press(key, 0)
    view.on_key_release(key, 0)


# ---------------------------------------------------------------- demo keys

def test_demo_correct_wrong_and_counters(view):
    before = (view.system.snapshot(), view.system.stats())
    press(view, arcade.key.W)                    # extra milk: refused, nothing changes
    assert not view.latest.success
    assert (view.system.snapshot(), view.system.stats()) == before
    assert view.effects.shake_time > 0
    press(view, arcade.key.C)
    stats = view.system.stats()
    assert view.latest.success and stats.completed == 1 and stats.score > 0
    assert "serve_success" in view.sound.history and "serve_fail" in view.sound.history
    view.on_draw()


def test_demo_time_skip_expires_orders_and_pause_freezes_time(view):
    press(view, arcade.key.P)
    paused = view.system.snapshot()
    view.on_update(100.0)
    press(view, arcade.key.T)                    # ignored while paused
    assert view.system.snapshot() == paused
    view.on_draw()
    press(view, arcade.key.P)
    press(view, arcade.key.Y)                    # 60 s > 45 s patience
    assert view.system.stats().expired >= 1              # every live timer ran down
    assert "expired" in view.latest.message and "order_expired" in view.sound.history
    view.on_update(0.2)
    view.on_draw()


def test_demo_key_repeat_is_one_action_and_reset_starts_a_new_day(view):
    view.on_key_press(arcade.key.C, 0)
    view.on_key_press(arcade.key.C, 0)           # auto-repeat while held
    assert view.system.stats().completed == 1
    view.on_key_release(arcade.key.C, 0)
    press(view, arcade.key.R)
    stats = view.system.stats()
    assert (stats.accepted, stats.completed, stats.score) == (1, 0, 0)
    assert view.system.snapshot()[0].order_id == 1
    muted = view.sound.muted
    press(view, arcade.key.M)
    assert view.sound.muted is not muted


def test_demo_can_finish_a_day_with_confetti(view):
    for _ in range(12):
        press(view, arcade.key.C)
        view.on_update(2.1)                      # the next customer comes in
        if view.system.is_day_complete:
            break
    assert view.system.is_day_complete and view.system.stats().score >= RULES.target_gold
    assert any(p.kind == "confetti" for p in view.effects.particles)
    view.on_draw()


# ---------------------------------------------------------------- sidebar

def card(order_id, status="accepted", remaining=30.0, required=("sandwich", "tomato")):
    return OrderSnapshot(order_id, "Tomato sandwich", required, remaining, status, 120.0, 65)


def test_helpers_colour_blink_and_greyscale(view):
    assert timer_color(0.9) != timer_color(0.4) != timer_color(0.1)
    # int(t * 5) % 2: the state flips five times a second (every 0.2 s).
    assert blink_on(0.1) and not blink_on(0.3) and blink_on(0.5)
    sidebar = OrderSidebar(PANEL)
    colour = sidebar.icons["tomato"].image.convert("RGB").getpixel((60, 70))
    grey = greyscale_texture(sidebar.icons["tomato"]).image.convert("RGB").getpixel((60, 70))
    assert max(colour) - min(colour) > 60 and grey[0] == grey[1] == grey[2]
    assert sidebar.grey_icons["tomato"].image.getchannel("A").tobytes() == \
           sidebar.icons["tomato"].image.getchannel("A").tobytes()


def test_sidebar_never_changes_what_it_draws(view):
    sidebar = OrderSidebar(PANEL)
    orders = (card(1), card(2, remaining=118.0), card(3, remaining=4.0, required=("pasta",)))
    stats = OrderStats(2, 5, 1, 320, 400)
    for _ in range(4):
        sidebar.update(0.1, orders)
        sidebar.draw(orders, stats)
    assert orders == (card(1), card(2, remaining=118.0), card(3, remaining=4.0, required=("pasta",)))
    assert stats == OrderStats(2, 5, 1, 320, 400)
    sidebar.draw((), OrderStats(0, 0, 0, 0, 0))   # empty board and no target also draw


def test_cards_slide_in_keep_inside_the_panel_and_close_gaps(view):
    sidebar = OrderSidebar(PANEL)
    orders = (card(1), card(2), card(3))
    sidebar.update(0.0, orders)
    first = sidebar._cards[1]
    assert first.slide > PANEL[2]                 # starts beyond the right edge
    for _ in range(60):
        sidebar.update(1 / 60, orders)
    assert abs(first.slide) < 1
    bottoms = [sidebar._cards[i].y for i in (1, 2, 3)]
    assert bottoms == sorted(bottoms, reverse=True)           # oldest on top
    assert min(bottoms) >= PANEL[1] and max(bottoms) + 94 <= PANEL[1] + PANEL[3] - 62
    # Order 1 is served: it lingers with a banner, then the others move up.
    sidebar.notify(OrderEvent("served", 1, "Tomato sandwich", 70))
    remaining = orders[1:]
    sidebar.update(0.1, remaining)
    assert sidebar._cards[1].ghost == "served" and sidebar._cards[1].gold == 70
    sidebar.draw(remaining, OrderStats(3, 1, 0, 70, 200))
    for _ in range(int((GHOST_SECONDS + 0.6) * 60)):
        sidebar.update(1 / 60, remaining)
    assert 1 not in sidebar._cards
    assert sidebar._cards[2].y == pytest.approx(bottoms[0], abs=1.0)
    sidebar.notify(OrderEvent("expired", 2, "Tomato sandwich"))
    sidebar.update(0.1, remaining[1:])
    assert sidebar._cards[2].ghost == "expired"
    sidebar.draw(remaining[1:], OrderStats(3, 1, 1, 70, 200))
    sidebar.reset()
    assert not sidebar._cards and sidebar.shown_gold == 0


def test_gold_counter_counts_up_to_the_real_total(view):
    sidebar = OrderSidebar(PANEL)
    sidebar.draw((), OrderStats(1, 1, 0, 80, 200))
    sidebar.update(1 / 60)
    assert 0 < sidebar.shown_gold < 80            # still counting
    for _ in range(120):
        sidebar.update(1 / 60)
    assert sidebar.shown_gold == 80


def test_sidebar_works_without_artwork(view, tmp_path, monkeypatch):
    monkeypatch.setattr("restaurant.orders.sidebar.FOOD_DIR", tmp_path)
    sidebar = OrderSidebar(PANEL)
    assert not sidebar.icons
    orders = (card(1), card(2, remaining=2.0))
    sidebar.update(0.5, orders)
    sidebar.draw(orders, OrderStats(1, 0, 0, 0, 200))   # coloured placeholders


# ---------------------------------------------------------------- effects

def test_effects_run_on_delta_time_and_clean_up_after_themselves(view):
    effects = OrderEffects(seed=1)
    assert effects.shake_offset == (0.0, 0.0)
    effects.served(300, 300, 67)
    assert any(p.kind == "coin" for p in effects.particles)
    assert effects.texts[-1].value == "+67 G"
    start_y = effects.texts[-1].y
    effects.rejected(300, 300)
    assert effects.shake_offset != (0.0, 0.0) and effects.flash > 0
    effects.update(0.1)
    assert effects.texts[0].y > start_y            # the gold text floats upward
    effects.draw(None, (744, 640))
    effects.draw_hatch_call(300, 300, True)
    for _ in range(400):
        effects.update(1 / 60)
    assert not effects.particles and not effects.texts
    assert effects.shake_offset == (0.0, 0.0) and effects.flash == 0
    effects.celebrate(700, 600)
    assert len(effects.particles) <= OrderEffects.MAX_PARTICLES
    effects.reset()
    assert not effects.particles


def test_coins_bounce_on_their_floor_instead_of_falling_forever(view):
    effects = OrderEffects(seed=2)
    effects.served(300, 300, 50)
    coins = [p for p in effects.particles if p.kind == "coin"]
    floors = {id(c): c.floor for c in coins}
    for _ in range(50):
        effects.update(1 / 60)
    for coin in [p for p in effects.particles if p.kind == "coin"]:
        assert coin.y >= floors[id(coin)] - 12


def test_real_system_feeds_the_sidebar_end_to_end(view):
    system, sidebar = OrderSystem(3, RULES), OrderSidebar(PANEL)
    for _ in range(200):
        system.update(0.25)
        for event in system.drain_events():
            sidebar.notify(event)
        sidebar.update(0.25, system.snapshot())
        sidebar.draw(system.snapshot(), system.stats())
    assert system.stats().expired > 0
    assert len(sidebar._cards) <= RULES.max_cards + 2     # live cards plus brief ghosts
