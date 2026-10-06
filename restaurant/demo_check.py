"""Small executable-level check; works without pytest or the source repository."""
import json
import traceback
from pathlib import Path

import arcade

from restaurant.game_view import create_window


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
                view.player.reset((220, 300))
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
            view.player.reset((450, 275))
            view.on_key_press(arcade.key.W, 0)
            for _ in range(20):
                view.on_update(0.25)
            check(view.player.position[1] < 320, "Counter blocks movement")
            check(not arcade.check_for_collision_with_list(view.player.sprite, view.walls),
                  "Chef remains outside solid counters")
            view.clear_input()
            view.on_key_press(arcade.key.E, 0)
            view.on_key_press(arcade.key.E, 0)
            view.on_update(0.01)
            check(view.interaction_count == 1 and "plate" in view.message,
                  "Exactly one nearby interaction per key press")
            view.on_key_press(arcade.key.P, 0)
            before = view.player.position
            view.on_update(1)
            check(view.player.position == before and view.paused, "Pause freezes player")
            view.on_key_release(arcade.key.P, 0)
            view.on_key_press(arcade.key.P, 0)
            view.on_draw()
            arcade.get_image().save(output / "demo.png")
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
