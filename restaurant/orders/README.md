# Order system

| File | What it is | Imports Arcade? |
| --- | --- | --- |
| `models.py` | Menu (`RECIPES`), `DayRules`, the private order record | No |
| `system.py` | `OrderSystem`: arrivals, timers, matching, gold, day target | No |
| `sidebar.py` | `OrderSidebar`: animated gold meter and order cards | Yes |
| `effects.py` | `OrderEffects`: coins, floating gold, screen shake, confetti | Yes |

## The life of an order

```text
arrives -> live at once, timer starts   bell, "!" over the hatch, card slides in
   |-- try_serve(plate, food) / try_serve_held(food) in time --> served, gold paid
   '-- timer reaches zero first ------------------------------> expired, no gold
```

## Public API

```python
orders = OrderSystem(seed=None, rules=DayRules())
orders.update(dt)                    # each unpaused frame, BEFORE handling key presses
orders.try_serve(plate, food)        # carried plate; consumes that exact revision
orders.try_serve_held(food)          # a sandwich or milk handed over directly
orders.snapshot()                    # -> tuple[OrderSnapshot, ...], oldest first
orders.stats()                       # -> OrderStats(accepted=arrived, completed, expired, score=gold, target)
orders.drain_events()                # -> OrderEvent records for effects and sound
orders.reset(seed=None, rules=None)  # a new day
orders.is_day_complete, orders.active_count
```

- Matching uses `Counter` (quantities count, placement order does not) and
  `recipe_item`, so a chopped tomato fills a "tomato" slot.
- A failed serve changes nothing. Success consumes the plate through
  `food.serve_plate(revision)` before any order changes, so one plate can
  never be paid twice. The chef keeps the empty plate.
- Gold = recipe base price + speed tip (`tip_max` x share of patience left).
- Day tuning lives in `restaurant/kitchen/days.py`; the menu in `models.py`.

```shell
python -m demos.orders_demo
python -m pytest tests/test_orders.py -q
```
