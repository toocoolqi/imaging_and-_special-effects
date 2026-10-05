"""Launch source with python main.py, or double-click the packaged Windows app."""
import argparse
from pathlib import Path

import arcade
from restaurant.game_view import create_window


def main():
    parser = argparse.ArgumentParser(description="Classic Chef player demo")
    parser.add_argument("--self-test", type=Path, metavar="OUTPUT_FOLDER",
                        help="Check the packaged app in a hidden window and save a report.")
    args = parser.parse_args()
    if args.self_test is not None:
        from restaurant.demo_check import run_packaged_check
        raise SystemExit(run_packaged_check(args.self_test))
    create_window()
    arcade.run()


if __name__ == "__main__":
    main()
