"""
Menu definitions for the fast food ordering system.
"""

# Menu items with their base prices
MENU_ITEMS = {
    "burger": {
        "name": "Burger",
        "base_price": 5.99,
        "description": "Classic beef burger with lettuce, tomato, and cheese"
    },
    "chicken_burger": {
        "name": "Chicken Burger",
        "base_price": 6.49,
        "description": "Grilled chicken with lettuce, tomato, and mayo"
    },
    "veggie_burger": {
        "name": "Veggie Burger",
        "base_price": 5.49,
        "description": "Plant-based patty with fresh vegetables"
    },
    "taco": {
        "name": "Taco",
        "base_price": 3.99,
        "description": "Soft shell taco with beef, lettuce, cheese, and salsa"
    },
    "burrito": {
        "name": "Burrito",
        "base_price": 7.99,
        "description": "Large flour tortilla filled with rice, beans, and your choice of protein"
    },
    "chicken_burrito": {
        "name": "Chicken Burrito",
        "base_price": 8.49,
        "description": "Large flour tortilla filled with rice, beans, and grilled chicken"
    },
    "quesadilla": {
        "name": "Quesadilla",
        "base_price": 6.99,
        "description": "Grilled tortilla filled with cheese and your choice of protein"
    },
    "nachos": {
        "name": "Nachos",
        "base_price": 5.99,
        "description": "Tortilla chips topped with cheese, jalapeños, and salsa"
    },
    "fries": {
        "name": "Fries",
        "base_price": 2.99,
        "description": "Crispy golden fries"
    },
    "onion_rings": {
        "name": "Onion Rings",
        "base_price": 3.49,
        "description": "Crispy battered onion rings"
    },
    "soda": {
        "name": "Soda",
        "base_price": 1.99,
        "description": "Refreshing carbonated drink"
    },
    "cola": {
        "name": "Cola",
        "base_price": 1.99,
        "description": "Classic cola soda"
    },
    "diet_cola": {
        "name": "Diet Cola",
        "base_price": 1.99,
        "description": "Sugar-free cola soda"
    },
    "lemon_lime": {
        "name": "Lemon-Lime Soda",
        "base_price": 1.99,
        "description": "Refreshing lemon-lime soda"
    },
    "orange_soda": {
        "name": "Orange Soda",
        "base_price": 1.99,
        "description": "Sweet orange flavored soda"
    },
    "iced_tea": {
        "name": "Iced Tea",
        "base_price": 1.99,
        "description": "Refreshing iced tea"
    },
    "water": {
        "name": "Water",
        "base_price": 1.49,
        "description": "Bottled water"
    }
}

# Size options with price modifiers
SIZES = {
    "small": {
        "name": "Small",
        "price_modifier": 0.0,  # No additional cost
        "description": "Small portion"
    },
    "medium": {
        "name": "Medium",
        "price_modifier": 1.50,
        "description": "Medium portion"
    },
    "large": {
        "name": "Large",
        "price_modifier": 2.50,
        "description": "Large portion"
    }
}

# Combo deals
COMBOS = {
    "regular_combo": {
        "name": "Regular Combo",
        "includes": ["fries", "soda"],
        "discount": 1.50,  # Discount compared to ordering items separately
        "description": "Includes regular fries and a medium drink"
    },
    "large_combo": {
        "name": "Large Combo",
        "includes": ["fries", "soda"],
        "size": "large",
        "discount": 2.00,
        "description": "Includes large fries and a large drink"
    }
}

# Customization options with pricing
CUSTOMIZATIONS = {
    "no_mayo": {"name": "No mayonnaise", "price": 0.0},
    "no_cheese": {"name": "No cheese", "price": 0.0},
    "no_lettuce": {"name": "No lettuce", "price": 0.0},
    "no_tomato": {"name": "No tomato", "price": 0.0},
    "no_onion": {"name": "No onion", "price": 0.0},
    "extra_cheese": {"name": "Extra cheese", "price": 0.75},
    "extra_sauce": {"name": "Extra sauce", "price": 0.50},
    "gluten_free_bun": {"name": "Gluten-free bun", "price": 1.50},
    "beef": {"name": "Beef", "price": 0.75},
    "lettuce": {"name": "Lettuce", "price": 0.0},
    "cheese": {"name": "Cheese", "price": 0.50},
    "salsa": {"name": "Salsa", "price": 0.25}
}

# Protein options for certain items
PROTEIN_OPTIONS = {
    "beef": {"name": "Beef", "price": 0.75},
    "chicken": {"name": "Grilled Chicken", "price": 0.0},
    "steak": {"name": "Steak", "price": 1.50},
    "veggie": {"name": "Plant-based protein", "price": 0.0}
}

# Drink options
DRINK_OPTIONS = {
    "cola": "Cola",
    "diet_cola": "Diet Cola",
    "lemon_lime": "Lemon-Lime Soda",
    "orange": "Orange Soda",
    "iced_tea": "Iced Tea"
}

def get_formatted_menu():
    """Return a formatted menu for display purposes."""
    menu_text = "=== GrillTalk MENU ===\n\n"
    
    # Main items
    menu_text += "MAIN ITEMS:\n"
    for item_id, item in MENU_ITEMS.items():
        if item_id not in ["fries", "onion_rings", "soda", "water"]:
            menu_text += f"- {item['name']}: ${item['base_price']:.2f} - {item['description']}\n"
    
    # Sides
    menu_text += "\nSIDES:\n"
    for item_id in ["fries", "onion_rings"]:
        item = MENU_ITEMS[item_id]
        menu_text += f"- {item['name']}: ${item['base_price']:.2f} - {item['description']}\n"
    
    # Drinks
    menu_text += "\nDRINKS:\n"
    for item_id in ["soda", "cola", "diet_cola", "lemon_lime", "orange_soda", "iced_tea", "water"]:
        if item_id in MENU_ITEMS:
            item = MENU_ITEMS[item_id]
            menu_text += f"- {item['name']}: ${item['base_price']:.2f} - {item['description']}\n"
    
    # Sizes
    menu_text += "\nSIZES:\n"
    for size_id, size in SIZES.items():
        modifier_text = f"+${size['price_modifier']:.2f}" if size['price_modifier'] > 0 else "No additional cost"
        menu_text += f"- {size['name']}: {modifier_text}\n"
    
    # Combos
    menu_text += "\nCOMBO DEALS:\n"
    for combo_id, combo in COMBOS.items():
        menu_text += f"- {combo['name']}: Save ${combo['discount']:.2f} - {combo['description']}\n"
    
    return menu_text

def calculate_order_price(order_items):
    """
    Calculate the total price of an order.
    
    Args:
        order_items: List of dictionaries containing order details
        
    Returns:
        float: Total price of the order
    """
    total = 0.0
    
    for item in order_items:
        # Make a deep copy of the item to avoid reference issues
        item = dict(item)
        
        base_item = MENU_ITEMS.get(item.get("item_id"))
        if not base_item:
            continue
            
        item_price = base_item["base_price"]
        
        # Add size modifier if applicable
        size = item.get("size")
        if size and size in SIZES:
            item_price += SIZES[size]["price_modifier"]
            
        # Handle combo pricing
        if item.get("combo"):
            combo_type = item.get("combo_type", "regular_combo")
            if combo_type in COMBOS:
                # For combo pricing, we need to:
                # 1. Start with the base item price
                # 2. Add the price of included items (fries and drink)
                # 3. Subtract the combo discount
                
                combo_price = item_price  # Start with base item price
                
                # Add the price of the included items
                for included_item in COMBOS[combo_type]["includes"]:
                    if included_item in MENU_ITEMS:
                        included_price = MENU_ITEMS[included_item]["base_price"]
                        
                        # Apply size to included items if specified in the combo
                        if "size" in COMBOS[combo_type] and COMBOS[combo_type]["size"] in SIZES:
                            combo_size = COMBOS[combo_type]["size"]
                            included_price += SIZES[combo_size]["price_modifier"]
                            
                        combo_price += included_price
                
                # Apply the combo discount
                combo_price -= COMBOS[combo_type]["discount"]
                
                # Use the combo price
                item_price = combo_price
        
        # Add customization costs
        customizations = item.get("customizations", [])
        for custom in customizations:
            if custom in CUSTOMIZATIONS:
                item_price += CUSTOMIZATIONS[custom]["price"]
                
        # Add protein upgrade costs
        protein = item.get("protein")
        if protein and protein in PROTEIN_OPTIONS:
            item_price += PROTEIN_OPTIONS[protein]["price"]
            
        # Multiply by quantity
        quantity = item.get("quantity", 1)
        item_price *= quantity
            
        total += item_price
        
    return round(total, 2)
