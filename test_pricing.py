#!/usr/bin/env python3

from menu import calculate_order_price

# Test 2x Regular Taco Regular Combo with extra cheese
order_items = [
    {
        "item_id": "taco",
        "quantity": 2,
        "size": "regular",
        "combo": True,
        "combo_type": "regular_combo",
        "customizations": ["extra_cheese"],
        "protein": None,
        "drink_choice": None
    }
]

price = calculate_order_price(order_items)
print(f"2x Regular Taco Regular Combo with extra cheese: ${price}")

# Let's also test 1x to see the base price
order_items_single = [
    {
        "item_id": "taco",
        "quantity": 1,
        "size": "regular",
        "combo": True,
        "combo_type": "regular_combo",
        "customizations": ["extra_cheese"],
        "protein": None,
        "drink_choice": None
    }
]

price_single = calculate_order_price(order_items_single)
print(f"1x Regular Taco Regular Combo with extra cheese: ${price_single}")
print(f"Double check: 2 × ${price_single} = ${2 * price_single}")
