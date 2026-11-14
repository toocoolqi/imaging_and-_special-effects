"""Snapshot-only order cards in the shared kitchen viewport."""
from collections import Counter
from math import ceil

import arcade

from restaurant.kitchen.scene import draw_icon
from restaurant.orders.system import BONUS_SECONDS, ORDER_SECONDS


class OrderSidebar:
    def __init__(self, bounds):
        self.bounds = bounds

    def draw(self, orders, stats, textures, text):
        x, bottom, width, height = self.bounds
        top = bottom + height
        arcade.draw_lbwh_rectangle_filled(*self.bounds, (24, 37, 44))
        text("orders_heading", "Service orders", x + 16, top - 34, 21)
        text("orders_stats", f"Score {stats.score}   Accepted {stats.accepted}\nCompleted {stats.completed}   Expired {stats.expired}",
             x + 16, top - 49, 11, (111, 221, 178), multiline=True,
             width=width - 32, anchor_y="top")
        if not orders:
            text("orders_waiting", "Press E at the service table to start.", x + 16, top - 104,
                 13, multiline=True, width=width - 32, anchor_y="top")
        for index, order in enumerate(orders):
            y = top - 96 - index * 119
            quick = ORDER_SECONDS - order.remaining_seconds <= BONUS_SECONDS
            accent = (240, 199, 124) if quick else (111, 221, 178)
            arcade.draw_lbwh_rectangle_filled(x + 12, y - 110, width - 24, 110, (37, 53, 60))
            arcade.draw_lbwh_rectangle_filled(x + 12, y - 110, 3, 110, accent)
            text(f"order_name_{index}", f"#{order.order_id}  {order.recipe_name}", x + 23, y - 23, 13)
            minutes, seconds = divmod(ceil(order.remaining_seconds), 60)
            bonus = "  ·  Fast bonus" if quick else ""
            text(f"order_status_{index}", f"{minutes}:{seconds:02d}{bonus}", x + 23, y - 44, 11, accent)
            for slot, (food, count) in enumerate(Counter(order.required).items()):
                col = x + 23 + (slot % 2) * 105
                row = y - 66 - (slot // 2) * 30
                draw_icon(textures[food], col + 10, row, 23)
                text(f"order_{index}_food_{slot}", f"×{count} {food.replace('_', ' ')}",
                     col + 24, row - 4, 9)
