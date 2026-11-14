"""Small executable-level check; works without pytest or the source repository."""
import json
import traceback
from pathlib import Path

import arcade

from restaurant.game_view import create_window
from restaurant.display import window_geometry
from restaurant.kitchen.layout import ANIMATION_TEST_POSITION, PROPS
from restaurant.player.controller import FOOT_HALF_HEIGHT, FOOT_HALF_WIDTH, FOOT_OFFSET_Y
from restaurant.shared.contracts import PlateLocation, PotStage
from restaurant.shared.settings import (
    KITCHEN_HEIGHT, KITCHEN_WIDTH, PLAYER_SCALE, PLAYER_SPEED, TARGETS, WINDOW_HEIGHT, WINDOW_WIDTH,
)


def exercise_service(view, output, check):
    """Exercise two orders with the production keys and capture rendered states."""
    targets = {target.target_id: target for target in TARGETS}

    def use():
        view.on_key_press(arcade.key.E, 0)
        view.on_update(0)
        view.on_key_release(arcade.key.E, 0)

    def station(name):
        target = targets[name]
        view.player.reset((target.x, target.y))
        use()

    def capture(name):
        view.on_draw()
        arcade.get_image().save(output / name)

    def serve_and_return(completed):
        station("serve")
        plate = view.ingredients.snapshot().plate
        check(plate.location is PlateLocation.CARRIED and not plate.ingredients
              and view.orders.stats().score == 150 * completed,
              f"Order {completed} served once; empty plate remains carried")
        capture(f"order-{completed}-served.png")
        # Walk down the east aisle, then turn west below the plate counter.
        serve, home = targets["serve"], targets["plate"]
        for key, distance in ((arcade.key.S, serve.y - home.y),
                              (arcade.key.A, serve.x - home.x)):
            view.on_key_press(key, 0)
            remaining = distance / PLAYER_SPEED
            while remaining > 1e-8:
                step = min(remaining, 1 / 60)
                view.on_update(step)
                remaining -= step
            view.on_key_release(key, 0)
        check(view.selected == home, "Walked the empty plate back to its table")
        use()
        check(view.ingredients.snapshot().plate.location is PlateLocation.DOCKED,
              "Returned the same empty plate")

    view.reset()
    station("serve")
    station("plate")
    for item in ("sandwich", "tomato"):
        station(f"box_{item}")
    serve_and_return(1)

    station("plate")
    for item in ("noodles", "milk", "tomato"):
        station(f"box_{item}")
    station("pot")
    check(view.ingredients.snapshot().pot.stage is PotStage.COOKING,
          "Noodles, milk, and tomato start cooking")
    view.on_update(1)
    capture("cooking-pasta.png")
    view.on_update(3)
    check(view.ingredients.snapshot().pot.stage is PotStage.READY,
          "Pot finishes after four seconds")
    station("pot")
    capture("plated-pasta.png")
    view.on_update(12)
    serve_and_return(2)
    capture("plate-returned.png")


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
            view = window.current_view
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
            check(view.player.sprite.height >= table.height * 0.75,
                  "Chef is proportionate to the furniture")
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
                check(view.player.state == "idle" and view.player.direction == direction,
                      f"{direction} idle and facing")

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
            chop = next(target for target in TARGETS if target.kind == "chop")
            view.reset()
            view.player.reset((chop.x, chop.y))
            view.on_key_press(arcade.key.E, 0)
            view.on_update(0.01)
            check(view.interaction_count == 1 and "Cutting" in view.message,
                  "Chopping board preview hook; food stays decorative")
            # Verify task2 is usable in the combined room and bundled assets.
            view.clear_input()
            box = next(t for t in TARGETS if t.ingredient_id == "tomato")
            view.player.reset((box.x, box.y))
            view.on_key_press(arcade.key.E, 0)
            view.on_update(0.01)
            check(view.ingredients.snapshot().held == "tomato", "Task2 pickup in the shared kitchen")
            view.clear_input()
            view.player.reset((plate.x, plate.y))
            view.on_key_press(arcade.key.E, 0)
            view.on_update(0.01)
            check(view.ingredients.snapshot().plate.ingredients == ("tomato",),
                  "Task2 places collected food onto the shared kitchen plate")
            view.on_draw()
            arcade.get_image().save(output / "food-on-plate.png")
            preview_message = view.message
            serve = next(target for target in TARGETS if target.kind == "serve")
            view.reset()
            view.player.reset((serve.x, serve.y))
            view.on_key_press(arcade.key.E, 0)
            view.on_update(0.01)
            check(view.selected == serve and len(view.orders.snapshot()) == 1,
                  "Service table starts the first order")
            view.clear_input()
            view.player.reset((chop.x, chop.y))
            view.on_key_press(arcade.key.P, 0)
            before = view.player.position
            view.on_update(1)
            check(view.player.position == before and view.paused, "Pause freezes player")
            view.on_key_release(arcade.key.P, 0)
            view.on_key_press(arcade.key.P, 0)
            view.clear_input()
            view.message = preview_message
            view.on_update(0.01)
            view.on_draw()
            arcade.get_image().save(output / "demo.png")
            view.debug = True
            view.on_draw()
            arcade.get_image().save(output / "collision-guide.png")
            view.debug = False
            exercise_service(view, output, check)
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
        window = create_window(visible=False)
        arcade.schedule(exercise, 0.25)
        arcade.run()
    except Exception:
        report["error"] = traceback.format_exc()
        if window is not None:
            window.close()
    finally:
        (output / "self-test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1
