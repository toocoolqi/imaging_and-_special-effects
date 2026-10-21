"""Small executable-level check; works without pytest or the source repository."""
import json
import traceback
from pathlib import Path

import arcade

from restaurant.game_view import create_window
from restaurant.kitchen.layout import ANIMATION_TEST_POSITION
from restaurant.shared.settings import KITCHEN_HEIGHT, KITCHEN_WIDTH, TARGETS


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
            check(view.player.position[1] < 140, "Plate counter blocks movement")
            check(not arcade.check_for_collision_with_list(view.player.sprite, view.walls),
                  "Chef remains outside solid counters")
            view.clear_input()
            view.on_key_press(arcade.key.E, 0)
            view.on_key_press(arcade.key.E, 0)
            view.on_update(0.01)
            check(view.interaction_count == 1 and "plate" in view.message,
                  "Exactly one nearby interaction per key press")
            # Exercise each actual kitchen obstacle, not just a synthetic wall.
            for index, wall in enumerate(view.walls):
                tested = 0
                half_x = view.player.sprite.width * 24 / 56
                half_y = view.player.sprite.height * 43 / 92
                for direction, point in (
                    ("right", (wall.left - half_x - 8, wall.center_y)),
                    ("left", (wall.right + half_x + 8, wall.center_y)),
                    ("up", (wall.center_x, wall.bottom - half_y - 8)),
                    ("down", (wall.center_x, wall.top + half_y + 8)),
                ):
                    if not (half_x <= point[0] <= KITCHEN_WIDTH - half_x
                            and half_y <= point[1] <= KITCHEN_HEIGHT - half_y):
                        continue
                    view.player.reset(point)
                    if arcade.check_for_collision_with_list(view.player.sprite, view.walls):
                        continue
                    view.player.set_move_key(direction, True)
                    for _ in range(12):
                        view.player.update(0.25, view.walls)
                        if arcade.check_for_collision_with_list(view.player.sprite, view.walls):
                            raise AssertionError(f"Obstacle {index} overlaps the chef")
                    if direction == "right":
                        assert view.player.sprite.center_x < wall.left
                    elif direction == "left":
                        assert view.player.sprite.center_x > wall.right
                    elif direction == "up":
                        assert view.player.sprite.center_y < wall.bottom
                    else:
                        assert view.player.sprite.center_y > wall.top
                    tested += 1
                check(tested > 0, f"Kitchen obstacle {index + 1}: solid from clear approaches")
            chop = next(target for target in TARGETS if target.kind == "chop")
            view.reset()
            view.player.reset((chop.x, chop.y))
            view.on_key_press(arcade.key.E, 0)
            view.on_update(0.01)
            check(view.interaction_count == 1 and "Cutting" in view.message,
                  "Chopping board preview hook; food stays decorative")
            preview_message = view.message
            view.on_key_press(arcade.key.P, 0)
            before = view.player.position
            view.on_update(1)
            check(view.player.position == before and view.paused, "Pause freezes player")
            view.on_key_release(arcade.key.P, 0)
            view.on_key_press(arcade.key.P, 0)
            view.clear_input()
            view.message = preview_message
            view.on_draw()
            arcade.get_image().save(output / "demo.png")
            view.debug = True
            view.on_draw()
            arcade.get_image().save(output / "collision-guide.png")
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
