"""Small executable-level check; works without pytest or the source repository."""
import json
import traceback
from pathlib import Path

import arcade

from restaurant.game_view import create_window
from restaurant.display import window_geometry
from restaurant.hazards.navigation import routes_open
from restaurant.ingredients.chopping import CHOP_SECONDS
from restaurant.kitchen.layout import ANIMATION_TEST_POSITION, PROPS
from restaurant.kitchen.days import DAYS
from restaurant.menu import MainMenu, PLAY_BUTTON
from restaurant.orders.models import DayRules
from restaurant.pixel_art import ART_SIZE
from restaurant.player.controller import FOOT_HALF_HEIGHT, FOOT_HALF_WIDTH, FOOT_OFFSET_Y
from restaurant.shared.contracts import PlateLocation, PotStage
from restaurant.shared.settings import (
    KITCHEN_HEIGHT, KITCHEN_WIDTH, PLAYER_SCALE, TARGETS, WINDOW_HEIGHT, WINDOW_WIDTH,
)


def run_packaged_check(output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    report = {"passed": False, "checks": []}
    window = None

    def check(condition, description):
        if not condition:
            raise AssertionError(description)
        report["checks"].append(description)

    def exercise(delta_time):
        arcade.unschedule(exercise)
        try:
            menu = window.current_view
            check(isinstance(menu, MainMenu), "App opens on the main menu")
            menu.on_draw()
            arcade.get_image().save(output / "main-menu.png")
            viewport = menu.display_viewport()
            menu.on_mouse_press(
                viewport.left + PLAY_BUTTON.center_x * viewport.width / WINDOW_WIDTH,
                viewport.bottom + PLAY_BUTTON.center_y * viewport.height / WINDOW_HEIGHT,
                arcade.MOUSE_BUTTON_LEFT, 0)
            view = window.current_view
            check(view is not menu, "Clicking Play opens the first kitchen")
            view.on_draw()
            arcade.get_image().save(output / "kitchen.png")
            check(view.art.texture.size == ART_SIZE
                  and window.ctx.active_framebuffer is window.ctx.screen,
                  "Artwork shares one pixel grid and restores the display framebuffer")
            geometry = window_geometry(window)
            report["window"] = geometry
            work_left, work_top, work_width, work_height = geometry["work_area_pixels"]
            pixel_width, pixel_height = geometry["framebuffer_pixels"]
            fits = pixel_width <= work_width - 60 and pixel_height <= work_height - 96
            if "outer_rectangle_pixels" in geometry:
                left, top, right, bottom = geometry["outer_rectangle_pixels"]
                fits = fits and (left >= work_left and top >= work_top
                                 and right <= work_left + work_width
                                 and bottom <= work_top + work_height)
            check(fits, "Complete window fits desktop work area including DPI and frame")
            table = next(prop for prop in PROPS if prop.prop_id == "chopping_table")
            check(view.player.visual_height >= table.height * 1.5,
                  "Chef has a larger visual scale while retaining his collision footprint")
            check("back_wall" not in view.kitchen.textures,
                  "One consistent low top-down room; no perspective image strip")
            for key, direction, axis, sign in (
                (arcade.key.W, "up", 1, 1), (arcade.key.S, "down", 1, -1),
                (arcade.key.A, "left", 0, -1), (arcade.key.D, "right", 0, 1),
            ):
                view.reset()
                view.player.reset(ANIMATION_TEST_POSITION)
                before = view.player.position
                view.on_key_press(key, 0)
                view.on_update(0.14)
                frame = view.player.sprite.texture
                view.on_update(0.14)
                check((view.player.position[axis] - before[axis]) * sign > 30,
                      f"{direction} movement")
                check(view.player.sprite.texture is not frame, f"{direction} animation")
                view.on_draw()
                view.on_key_release(key, 0)
                view.on_update(0.01)
                check(view.player.pose == "idle" and view.player.direction == direction
                      and view.player.sprite.texture is not frame,
                      f"{direction} uses a directional standing pose after release")

            view.reset()
            plate = next(target for target in TARGETS if target.kind == "plate")
            view.player.reset((plate.x, plate.y))
            view.on_key_press(arcade.key.W, 0)
            for _ in range(20):
                view.on_update(0.25)
            plate_counter = next(prop for prop in PROPS if prop.prop_id == "plate_counter")
            _, base_y, _, base_h = plate_counter.collision_rectangle
            check(view.player.ground_position[1] < base_y - base_h / 2,
                  "Plate counter blocks movement")
            check(not arcade.check_for_collision_with_list(view.player.sprite, view.walls),
                  "Chef remains outside solid counters")
            view.clear_input()
            view.on_key_press(arcade.key.E, 0)
            view.on_key_press(arcade.key.E, 0)
            view.on_update(0.01)
            check(view.interaction_count == 1 and "plate" in view.message.lower(),
                  "Exactly one nearby interaction per key press")
            # Exercise each actual kitchen obstacle, not just a synthetic wall.
            for index, wall in enumerate(view.walls):
                tested = 0
                half_x = FOOT_HALF_WIDTH * PLAYER_SCALE
                half_y = FOOT_HALF_HEIGHT * PLAYER_SCALE
                approaches = []
                for fraction in (-0.25, 0, 0.25):
                    approaches.extend((
                        ("right", (wall.left - half_x - 2, wall.center_y + fraction * wall.height)),
                        ("left", (wall.right + half_x + 2, wall.center_y + fraction * wall.height)),
                        ("up", (wall.center_x + fraction * wall.width, wall.bottom - half_y - 2)),
                        ("down", (wall.center_x + fraction * wall.width, wall.top + half_y + 2)),
                    ))
                for direction, point in approaches:
                    if not (half_x <= point[0] <= KITCHEN_WIDTH - half_x
                            and half_y <= point[1] <= KITCHEN_HEIGHT - half_y):
                        continue
                    view.player.reset((point[0], point[1] - FOOT_OFFSET_Y * PLAYER_SCALE))
                    if arcade.check_for_collision_with_list(view.player.sprite, view.walls):
                        continue
                    view.player.set_move_key(direction, True)
                    for _ in range(12):
                        view.player.update(0.25, view.walls)
                        if arcade.check_for_collision_with_list(view.player.sprite, view.walls):
                            raise AssertionError(f"Obstacle {index} overlaps the chef")
                    if direction == "right":
                        assert view.player.ground_position[0] < wall.left
                    elif direction == "left":
                        assert view.player.ground_position[0] > wall.right
                    elif direction == "up":
                        assert view.player.ground_position[1] < wall.bottom
                    else:
                        assert view.player.ground_position[1] > wall.top
                    tested += 1
                check(tested > 0, f"Kitchen obstacle {index + 1}: solid from clear approaches")
            view.reset()

            def press(key):
                view.on_key_press(key, 0)
                view.on_update(0)
                view.on_key_release(key, 0)

            def use(target_id):
                target = next(item for item in view.targets if item.target_id == target_id)
                view.player.reset((target.x, target.y))
                press(arcade.key.E)

            # A scripted menu so the check always meets a tomato sandwich, then pasta.
            view.orders.reset(seed=1, rules=DayRules(150, 120.0, 12.0,
                                                     recipe_ids=("tomato_sandwich", "pasta")))
            first = view.orders.snapshot()[0]
            view.on_update(1.0)
            check(first.recipe_name == "Tomato sandwich"
                  and view.orders.snapshot()[0].remaining_seconds < first.remaining_seconds,
                  "The first order arrives live and its timer starts by itself")
            for food in ("tomato", "sandwich"):
                use(f"box_{food}")
                start_anchor = view.player.hand_anchor
                view.on_update(.18)
                check(view.ingredients.snapshot().held == food
                      and view.player.hand_anchor[1] > start_anchor[1],
                      f"Picking up {food} lifts it into the hand")
                view.on_draw()
                arcade.get_image().save(output / f"holding-{food}.png")
                use("bin")
            use("plate")
            check(view.ingredients.snapshot().plate.location is PlateLocation.CARRIED
                  and view.player.carrying_plate and view.player.pose == "idle",
                  "Task 2 empty plate pickup selects a carrying idle pose")
            use("box_tomato")
            check(view.ingredients.snapshot().plate.ingredients == ("tomato",),
                  "Task 2 pickups add directly to the carried plate")
            view.on_draw()
            arcade.get_image().save(output / "food-on-plate.png")

            view.player.reset(ANIMATION_TEST_POSITION)
            view.on_update(0)
            before = view.player.position
            view.on_key_press(arcade.key.D, 0)
            view.on_update(0.14)
            carry_walk = view.player.sprite.texture
            view.on_update(0.14)
            check(view.player.pose == "walk" and view.player.carrying_plate
                  and view.player.position[0] > before[0]
                  and view.player.sprite.texture is not carry_walk,
                  "Carrying the plate visibly animates while walking")
            view.on_draw()
            arcade.get_image().save(output / "carry-walk.png")
            view.on_key_release(arcade.key.D, 0)
            view.on_update(0.01)
            check(view.player.pose == "idle" and view.player.carrying_plate
                  and view.player.direction == "right",
                  "Releasing movement restores the side-facing carry idle")

            use("chopping_board")
            check(view.chopping.state == "chopping" and view.player.pose == "chop"
                  and not view.ingredients.snapshot().plate.ingredients,
                  "Chopping transfers a tomato to the board and starts the chop pose")
            chop_frame = view.player.sprite.texture
            view.on_update(CHOP_SECONDS / 4)
            check(view.player.sprite.texture is not chop_frame,
                  "Knife and arm advance through chopping frames")
            view.on_draw()
            arcade.get_image().save(output / "chopping.png")
            before = view.player.position, view.chopping.progress
            press(arcade.key.P)
            view.on_update(CHOP_SECONDS)
            check((view.player.position, view.chopping.progress) == before and view.paused,
                  "Pause freezes the player and chopping progress")
            press(arcade.key.P)
            view.on_update(CHOP_SECONDS)
            check(view.chopping.state == "ready", "Chopping completes after the animation")
            use("chopping_board")
            check(view.ingredients.snapshot().plate.ingredients == ("chopped_tomato",),
                  "Collect the chopped tomato from the board onto the plate")
            use("box_sandwich")
            use("serve")
            check(view.orders.stats().completed == 1 and view.total_gold > 0
                  and not view.ingredients.snapshot().plate.ingredients
                  and view.ingredients.snapshot().plate.location is PlateLocation.CARRIED,
                  "Serve chopped tomato sandwich and retain the same empty plate")
            check(any(p.kind == "coin" for p in view.effects.particles)
                  and view.effects.texts and view.effects.texts[-1].value.startswith("+"),
                  "Serving bursts coins and floats the gold earned above the hatch")
            view.on_update(2.1)
            check(view.orders.active_count >= 1
                  and view.orders.snapshot()[0].recipe_name == "Pasta",
                  "The next customer's pasta order arrives soon after")
            view.on_draw()
            arcade.get_image().save(output / "served.png")

            for ingredient in ("noodles", "milk", "tomato"):
                use(f"box_{ingredient}")
            use("pot")
            check(view.ingredients.snapshot().pot.stage is PotStage.COOKING,
                  "Task 2 cooks noodles, milk and tomato from the carried plate")
            view.on_update(11)
            use("pot")
            check(view.ingredients.snapshot().plate.ingredients == ("pasta",),
                  "Task 2 collects cooked pasta on the empty carried plate")
            use("serve")
            check(view.orders.stats().completed == 2 and view.day_complete,
                  "Pasta service earns gold and completes the day")
            use("plate")
            press(arcade.key.ENTER)
            check(view.day_index == 1, "Returning the plate lets the player open the next kitchen")
            # Every day uses its own prepared kitchen art and still works end to end.
            for index, day in enumerate(DAYS):
                view.go_to_day(index)
                view.fade = 0.0
                check(view.kitchen.room is not None
                      and (day.art_dir / "room.png").is_file(),
                      f"Day {index + 1} loads its {day.map_id} kitchen artwork")
                order = view.orders.snapshot()[0]
                if order.recipe_name in ("Sandwich", "Milk"):
                    use(f"box_{order.required[0]}")
                else:
                    use("plate")
                    for food in order.required:
                        if food == "pasta":
                            for raw in ("noodles", "milk", "tomato"):
                                use(f"box_{raw}")
                            use("pot")
                            view.on_update(4.5)
                            use("pot")
                        else:
                            use(f"box_{food}")
                view.on_update(0.3)
                view.on_draw()
                arcade.get_image().save(output / f"day{index + 1}-{day.map_id}.png")
                use("serve")
                check(view.orders.stats().completed == 1
                      and not arcade.check_for_collision_with_list(view.player.sprite, view.walls),
                      f"Day {index + 1} ({day.name}): an order is cooked and served")
            view.go_to_day(1)
            view.fade = 0.0
            view.on_draw()
            arcade.get_image().save(output / "demo.png")
            view.debug = True
            view.on_draw()
            arcade.get_image().save(output / "collision-guide.png")
            view.debug = False
            # Exercise new encounters through the same controller/inventory as
            # the playable app; these checks also run inside the portable EXE.
            view.go_to_day(0)
            view.fade = view.banner = 0
            view.ingredients.collect("sandwich")
            view.ingredients.add_to_plate()
            view.orders.reset(rules=DayRules(target_gold=999, patience_seconds=.2,
                                            arrival_seconds=.05, recipe_ids=("milk",)))
            view.on_update(.3)
            view.on_update(.05)
            check(view.encounters.ghost is not None and view.encounters.ghost.state == "warning",
                  "Two expired live orders trigger a ghost warning")
            view.orders.reset(rules=view.day.rules)
            for _ in range(160):
                view.on_update(.05)
                if view.encounters.ghost and view.encounters.ghost.food:
                    break
            ghost = view.encounters.ghost
            check(ghost is not None and ghost.food == ("sandwich",)
                  and view.ingredients.snapshot().plate.ingredients == (),
                  "Ghost steals food from a docked plate")
            view.player.reset((ghost.x - 50, ghost.y - 12))
            view.on_draw()
            arcade.get_image().save(output / "ghost-theft.png")
            press(arcade.key.E)
            check(view.encounters.ghost is None
                  and view.ingredients.snapshot().plate.ingredients == ("sandwich",),
                  "E reclaims stolen food and banishes the ghost")

            view.go_to_day(2)
            view.fade = view.banner = 0
            view.encounters.misses = 2
            view.on_update(.01)
            check(view.encounters.blocker is not None and view._blocker_wall is None,
                  "Hard-day guest warns before becoming solid")
            view.on_update(2.1)
            check(view._blocker_wall in view.walls
                  and routes_open(view.day.walls, view.encounters.stations,
                                  view.player.ground_position, view.encounters.blocker_rectangle),
                  "Solid guest preserves a route to every station")
            view.on_key_press(arcade.key.W, 0)
            for _ in range(20):
                view.on_update(.03)
            view.on_key_release(arcade.key.W, 0)
            check(view.player.ground_position[1] <= view._blocker_wall.bottom - 10
                  and not arcade.check_for_collision_with_list(view.player.sprite, view.walls),
                  "Guest collision stops the chef without penetration")
            view.player.reset((590, 267))
            view.on_draw()
            arcade.get_image().save(output / "blocking-guest.png")

            view.go_to_day(1)
            view.fade = view.banner = 0
            view.player.reset((480, 242))
            view.encounters.next_vampire = 0
            view.on_update(.01)
            check(view.encounters.vampire.state == "warning" and not view.encounters.stun,
                  "Vampire announces its lane before sweeping")
            view.on_draw()
            arcade.get_image().save(output / "vampire-warning.png")
            for _ in range(140):
                view.on_update(.025)
                if view.encounters.stun:
                    break
            check(view.encounters.stun > 0 and "vampire_bite" in view.audio.history,
                  "Vampire bite triggers brief stun and its sound")
            view.on_draw()
            arcade.get_image().save(output / "vampire-stun.png")
            before = view.player.position
            view.on_key_press(arcade.key.D, 0)
            view.on_update(.1)
            check(view.player.position == before, "Chef cannot move during stun")
            view.on_update(.8)
            check(view.encounters.stun == 0 and view.player.position[0] > before[0],
                  "Held movement resumes when stun ends")
            view.clear_input()
            left = view.shift_remaining
            press(arcade.key.P)
            view.on_update(8)
            check(view.shift_remaining == left, "Pause freezes the day deadline")
            press(arcade.key.P)

            view.go_to_day(3)
            view.fade = view.banner = 0
            view.shift_remaining = .03
            view.on_update(.04)
            check(view.failed and view.shift_remaining == 0, "Missing the gold target at the deadline fails the shift")
            view.on_draw()
            arcade.get_image().save(output / "shift-failed.png")
            press(arcade.key.ENTER)
            check(not view.failed and view.day_index == 3 and view.shift_remaining == 135,
                  "Enter retries the same day with a fresh timer")
            view.fade = view.banner = 0
            window.set_size(800, 600)
            view.on_draw()
            viewport = view.camera.viewport
            check(viewport.width <= window.width and viewport.height <= window.height
                  and abs(viewport.width / viewport.height - WINDOW_WIDTH / WINDOW_HEIGHT) < 0.01,
                  "Resizing keeps the whole room and sidebar visible without stretching")
            arcade.get_image().save(output / "resized-demo.png")
            report["passed"] = True
        except Exception:
            report["error"] = traceback.format_exc()
        finally:
            window.close()

    try:
        window = create_window(visible=False, show_menu=True)
        arcade.schedule(exercise, 0.25)
        arcade.run()
    except Exception:
        report["error"] = traceback.format_exc()
        if window is not None:
            window.close()
    finally:
        (output / "self-test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1
