# Member 3 starts here

Follow `docs/member_3_customer_orders.md`. Create `models.py`, `system.py` and
`sidebar.py` in this folder. Import the existing records from
`restaurant.shared.contracts`; do not redefine them.

Start with pure order state, timers and plate matching. Read a PlateSnapshot;
never mutate Member 2's plate directly. Then add the sidebar, independent demo
and tests. Orders appear in the sidebar; there are no walking customers.

No order behavior is implemented by this starter.
