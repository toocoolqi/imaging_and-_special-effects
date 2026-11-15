"""The board transforms one raw tomato without duplicating or losing it."""
from restaurant.ingredients.chopping import CHOP_SECONDS, ChoppingBoard
from restaurant.ingredients.system import IngredientSystem
from restaurant.orders.system import OrderSystem


def test_chopping_transfers_tomato_and_produces_one_platable_portion():
    board = ChoppingBoard()
    ingredients = IngredientSystem()
    assert not board.use(ingredients).success
    assert ingredients.collect("milk").success
    assert not board.use(ingredients).success
    assert ingredients.snapshot().held == "milk"
    ingredients.discard()
    assert ingredients.collect("tomato").success
    assert board.use(ingredients).success
    assert ingredients.snapshot().held is None
    assert board.state == "chopping"
    assert not board.use(ingredients).success
    assert not board.update(CHOP_SECONDS / 2)
    assert board.progress == 0.5
    assert board.update(CHOP_SECONDS / 2)
    assert not board.update(CHOP_SECONDS)
    assert board.state == "ready"

    assert ingredients.collect("sandwich").success
    assert not board.use(ingredients).success
    assert board.state == "ready"
    assert ingredients.snapshot().held == "sandwich"
    assert ingredients.add_to_plate().success
    assert board.use(ingredients).success
    assert ingredients.snapshot().held == "chopped_tomato"
    assert board.state == "idle"
    assert not board.use(ingredients).success
    assert ingredients.add_to_plate().success
    assert ingredients.snapshot().plate.ingredients == ("sandwich", "chopped_tomato")


def test_prepared_tomato_can_be_served_on_the_carried_plate():
    board = ChoppingBoard()
    ingredients = IngredientSystem()
    orders = OrderSystem(seed=1)
    assert orders.start().success
    assert ingredients.pickup_plate().success
    for food in ("sandwich", "tomato"):
        assert ingredients.collect(food).success
    assert board.use(ingredients).success
    assert ingredients.snapshot().plate.ingredients == ("sandwich",)
    assert board.update(CHOP_SECONDS)
    assert board.use(ingredients).success
    plate = ingredients.snapshot().plate
    assert plate.ingredients == ("sandwich", "chopped_tomato")
    assert ingredients.collect("tomato").success
    assert not orders.try_serve(ingredients.snapshot().plate, ingredients).success
    assert ingredients.return_plate().success
    assert ingredients.remove_from_plate().success
    assert ingredients.discard().success
    assert ingredients.pickup_plate().success
    plate = ingredients.snapshot().plate
    assert orders.try_serve(plate, ingredients).success
    assert ingredients.snapshot().plate.ingredients == ()


def test_prepared_tomato_supplies_one_pasta_slot():
    board = ChoppingBoard()
    ingredients = IngredientSystem()
    assert ingredients.pickup_plate().success
    for food in ("tomato", "noodles", "milk"):
        assert ingredients.collect(food).success
    assert board.use(ingredients).success
    assert board.update(CHOP_SECONDS)
    assert board.use(ingredients).success
    assert ingredients.collect("tomato").success
    assert ingredients.add_to_pot().success
    state = ingredients.snapshot()
    assert state.pot.ingredients == ("noodles", "milk", "tomato")
    assert state.plate.ingredients == ("tomato",)
