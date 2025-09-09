"""
Food ordering functionality for the voice agent.
"""

import json
from datetime import datetime
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams
from menu import MENU_ITEMS, SIZES, COMBOS, CUSTOMIZATIONS, PROTEIN_OPTIONS, DRINK_OPTIONS, calculate_order_price

# Import OrderSession for managing orders
from order_session import OrderSession

# Create a global order session
current_order_session = OrderSession()

# Import WebSocket functionality
try:
    from websocket_server import publish_order, publish_order_update, publish_final_order, clear_order
    WEBSOCKET_ENABLED = True
except ImportError:
    logger.warning("WebSocket server module not found. Order broadcasting disabled.")
    WEBSOCKET_ENABLED = False

def detect_invalid_item_id_patterns(item_id, menu_items, protein_options):
    """
    Detect and correct invalid item IDs that follow common patterns.
    This function is menu-agnostic and works with any menu structure.
    
    Args:
        item_id: The potentially invalid item ID
        menu_items: Dictionary of valid menu items
        protein_options: Dictionary of available protein options
        
    Returns:
        tuple: (corrected_item_id, suggested_protein)
        - corrected_item_id: The corrected item ID or original if no correction needed
        - suggested_protein: Protein to add if pattern suggests it, None otherwise
    """
    # If the item_id is already valid, no correction needed
    if item_id in menu_items:
        return item_id, None
    
    # Pattern 1: protein_item format (e.g., "beef_burrito", "chicken_taco", "steak_quesadilla")
    # Split on underscore and check if first part is a protein and second part is a menu item
    if "_" in item_id:
        parts = item_id.split("_", 1)  # Split only on first underscore
        if len(parts) == 2:
            potential_protein, potential_item = parts
            
            # Check if the first part is a valid protein and second part is a valid menu item
            if potential_protein in protein_options and potential_item in menu_items:
                return potential_item, potential_protein
    
    # Pattern 2: item_protein format (e.g., "burrito_beef", "taco_chicken")
    # Less common but possible
    if "_" in item_id:
        parts = item_id.split("_", 1)
        if len(parts) == 2:
            potential_item, potential_protein = parts
            
            # Check if the first part is a valid menu item and second part is a valid protein
            if potential_item in menu_items and potential_protein in protein_options:
                return potential_item, potential_protein
    
    # No pattern detected, return original
    return item_id, None

def find_item_variants(item_id, menu_items):
    """
    Find menu items that are variants of the same base item.
    This function dynamically identifies related items based on naming patterns.
    
    Args:
        item_id: The item ID to find variants for
        menu_items: Dictionary of valid menu items
        
    Returns:
        list: List of item IDs that are variants of the same base item
    """
    variants = [item_id]  # Always include the original item
    
    # Pattern 1: protein_item vs item (e.g., "chicken_burrito" vs "burrito")
    if "_" in item_id:
        # If current item has underscore, check if base item exists
        parts = item_id.split("_", 1)
        if len(parts) == 2:
            base_item = parts[1]
            if base_item in menu_items and base_item not in variants:
                variants.append(base_item)
    else:
        # If current item has no underscore, check for protein variants
        for menu_item_id in menu_items:
            if "_" in menu_item_id:
                parts = menu_item_id.split("_", 1)
                if len(parts) == 2 and parts[1] == item_id:
                    if menu_item_id not in variants:
                        variants.append(menu_item_id)
    
    return variants

def normalize_size_value(size_value):
    """
    Normalize size values for consistent comparison.
    Treats None, empty string, and "regular" as equivalent.
    
    Args:
        size_value: The size value to normalize
        
    Returns:
        str: Normalized size value
    """
    if not size_value or size_value in ["", "regular", "small"]:
        return "regular"
    return size_value

def detect_soda_type_conversion(item_id, drink_choice, menu_items):
    """
    Detect when LLM is trying to specify soda types using drink_choice parameter.
    Convert to appropriate item_id for specific soda types.
    
    Args:
        item_id: The item ID (usually "soda")
        drink_choice: The drink choice parameter
        menu_items: Dictionary of valid menu items
        
    Returns:
        str: Corrected item_id for specific soda type
    """
    if item_id == "soda" and drink_choice:
        # Map drink choices to specific soda item IDs
        soda_mapping = {
            "cola": "cola",
            "diet_cola": "diet_cola", 
            "lemon_lime": "lemon_lime",
            "orange": "orange_soda",
            "iced_tea": "iced_tea"
        }
        
        if drink_choice in soda_mapping and soda_mapping[drink_choice] in menu_items:
            return soda_mapping[drink_choice]
    
    return item_id

def normalize_combo_value(combo_value):
    """
    Normalize combo values for consistent comparison.
    Handles string/boolean conversion and various representations.
    
    Args:
        combo_value: The combo value to normalize
        
    Returns:
        bool: Normalized combo value
    """
    if isinstance(combo_value, str):
        # Handle explicit boolean strings
        if combo_value.lower() in ["true", "1", "yes"]:
            return True
        # Handle combo type strings (like "regular_combo", "large_combo")
        # If it's a string that ends with "_combo", treat it as True
        if combo_value.endswith("_combo"):
            return True
        # Handle "false", "0", "no" as False
        if combo_value.lower() in ["false", "0", "no"]:
            return False
        # Any other non-empty string is considered True
        return bool(combo_value.strip())
    return bool(combo_value)

def get_default_combo_type(combos):
    """
    Get the default combo type from available combos.
    Returns the first combo type available, or "regular_combo" as fallback.
    
    Args:
        combos: Dictionary of available combo types
        
    Returns:
        str: Default combo type ID
    """
    if not combos:
        return "regular_combo"  # Fallback if no combos defined
    
    # Return the first combo type, or prefer one with "regular" in the name
    combo_keys = list(combos.keys())
    regular_combos = [key for key in combo_keys if "regular" in key.lower()]
    
    if regular_combos:
        return regular_combos[0]
    else:
        return combo_keys[0]

def rebuild_item_description(item, menu_items, sizes, combos, protein_options):
    """
    Rebuild an item's description based on its current properties.
    
    Args:
        item: The item to rebuild the description for
        menu_items: Dictionary of menu items
        sizes: Dictionary of available sizes
        combos: Dictionary of available combos
        protein_options: Dictionary of available protein options
        
    Returns:
        Updated description string
    """
    item_id = item.get("item_id")
    if item_id not in menu_items:
        return item.get("description", "Unknown item")
        
    base_item = menu_items[item_id]
    quantity = item.get("quantity", 1)
    size = item.get("size", "regular")
    size_name = sizes.get(size, {}).get("name", "Regular") if size in sizes else "Regular"
    
    item_description = f"{quantity}x {size_name} {base_item['name']}"
    
    # Add combo information
    if normalize_combo_value(item.get("combo")):
        combo_type = item.get("combo_type", get_default_combo_type(combos))
        if combo_type in combos:
            item_description += f" {combos[combo_type]['name']}"
    
    # Add customizations
    customizations = item.get("customizations", [])
    custom_desc = []
    if customizations:
        custom_desc = []
        for c in customizations:
            if c in CUSTOMIZATIONS:
                custom_info = CUSTOMIZATIONS[c]
                name = custom_info["name"]
                price = custom_info["price"]
                if price > 0:
                    custom_desc.append(f"{name} (+${price:.2f})")
                else:
                    custom_desc.append(name)
        if custom_desc:
            item_description += f" ({', '.join(custom_desc)})"
    
    # Add protein choice
    protein = item.get("protein")
    if protein and protein in protein_options:
        protein_info = protein_options[protein]
        if protein_info["price"] > 0:
            item_description += f" with {protein_info['name']} (+${protein_info['price']:.2f})"
        else:
            item_description += f" with {protein_info['name']}"
    
    # Add drink choice for combos
    if normalize_combo_value(item.get("combo")) and item.get("drink_choice"):
        if item.get("drink_choice") in DRINK_OPTIONS:
            item_description += f", {DRINK_OPTIONS[item.get('drink_choice')]} drink"
    
    return item_description

def create_new_item_from_update(update_data, menu_items, sizes, combos, protein_options):
    """
    Create a new item from update data.
    
    Args:
        update_data: The update data to create the item from
        menu_items: Dictionary of menu items
        sizes: Dictionary of available sizes
        combos: Dictionary of available combos
        protein_options: Dictionary of available protein options
        
    Returns:
        New item dictionary
    """
    item_id = update_data.get("item_id")
    if item_id not in menu_items:
        return None
        
    # Create new item with default properties
    new_item = {
        "item_id": item_id,
        "quantity": update_data.get("quantity", 1),
        "size": update_data.get("size", "regular"),
        "combo": update_data.get("combo", False),
        "combo_type": update_data.get("combo_type"),
        "customizations": update_data.get("customizations", []),
        "protein": update_data.get("protein"),
        "drink_choice": update_data.get("drink_choice"),
    }
    
    # Build description
    new_item["description"] = rebuild_item_description(new_item, menu_items, sizes, combos, protein_options)
    
    # Calculate price
    new_item["price"] = calculate_order_price([new_item])
    
    return new_item
    """
    Rebuild an item's description based on its current properties.
    
    Args:
        item: The item to rebuild the description for
        menu_items: Dictionary of menu items
        sizes: Dictionary of available sizes
        combos: Dictionary of available combos
        protein_options: Dictionary of available protein options
        
    Returns:
        Updated description string
    """
    item_id = item.get("item_id")
    if item_id not in menu_items:
        return item.get("description", "Unknown item")
        
    base_item = menu_items[item_id]
    quantity = item.get("quantity", 1)
    size = item.get("size", "regular")
    size_name = sizes.get(size, {}).get("name", "Regular") if size in sizes else "Regular"
    
    item_description = f"{quantity}x {size_name} {base_item['name']}"
    
    # Add combo information
    if normalize_combo_value(item.get("combo")):
        combo_type = item.get("combo_type", get_default_combo_type(combos))
        if combo_type in combos:
            item_description += f" {combos[combo_type]['name']}"
    
    # Add customizations
    customizations = item.get("customizations", [])
    custom_desc = []
    if customizations:
        custom_desc = []
        for c in customizations:
            if c in CUSTOMIZATIONS:
                custom_info = CUSTOMIZATIONS[c]
                name = custom_info["name"]
                price = custom_info["price"]
                if price > 0:
                    custom_desc.append(f"{name} (+${price:.2f})")
                else:
                    custom_desc.append(name)
        if custom_desc:
            item_description += f" ({', '.join(custom_desc)})"
    
    # Add protein choice
    protein = item.get("protein")
    if protein and protein in protein_options:
        protein_info = protein_options[protein]
        if protein_info["price"] > 0:
            item_description += f" with {protein_info['name']} (+${protein_info['price']:.2f})"
        else:
            item_description += f" with {protein_info['name']}"
    
    # Add drink choice for combos
    if normalize_combo_value(item.get("combo")) and item.get("drink_choice"):
        if item.get("drink_choice") in DRINK_OPTIONS:
            item_description += f", {DRINK_OPTIONS[item.get('drink_choice')]} drink"
    
    return item_description
    """
    Rebuild an item's description based on its current properties.
    
    Args:
        item: The item to rebuild the description for
        menu_items: Dictionary of menu items
        sizes: Dictionary of available sizes
        combos: Dictionary of available combos
        protein_options: Dictionary of available protein options
        
    Returns:
        Updated description string
    """
    item_id = item.get("item_id")
    if item_id not in menu_items:
        return item.get("description", "Unknown item")
        
    base_item = menu_items[item_id]
    quantity = item.get("quantity", 1)
    size = item.get("size", "regular")
    size_name = sizes.get(size, {}).get("name", "Regular") if size in sizes else "Regular"
    
    item_description = f"{quantity}x {size_name} {base_item['name']}"
    
    # Add combo information
    if item.get("combo"):
        combo_type = item.get("combo_type", "regular_combo")
        if combo_type in combos:
            item_description += f" {combos[combo_type]['name']}"
    
    # Add customizations
    customizations = item.get("customizations", [])
    custom_desc = []
    if customizations:
        custom_desc = []
        for c in customizations:
            if c in CUSTOMIZATIONS:
                custom_info = CUSTOMIZATIONS[c]
                name = custom_info["name"]
                price = custom_info["price"]
                if price > 0:
                    custom_desc.append(f"{name} (+${price:.2f})")
                else:
                    custom_desc.append(name)
        if custom_desc:
            item_description += f" ({', '.join(custom_desc)})"
    
    # Add protein choice
    protein = item.get("protein")
    if protein and protein in protein_options:
        protein_info = protein_options[protein]
        if protein_info["price"] > 0:
            item_description += f" with {protein_info['name']} (+${protein_info['price']:.2f})"
        else:
            item_description += f" with {protein_info['name']}"
    
    # Add drink choice for combos
    if item.get("combo") and item.get("drink_choice"):
        if item.get("drink_choice") in DRINK_OPTIONS:
            item_description += f", {DRINK_OPTIONS[item.get('drink_choice')]} drink"
    
    return item_description

# Define the function schema for food ordering
food_order_function = FunctionSchema(
    name="order_food",
    description="Process a food order at GrillTalk fast food restaurant. IMPORTANT: ONLY use action='finalize' when the customer explicitly confirms they want to complete their order and pay. For making items into combos or updating sizes, use action='update_items' instead.",
    properties={
        "items": {
            "type": "array",
            "description": "List of items to order",
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "ID of the menu item (e.g., burger, taco, burrito)",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of this item to order",
                        "default": 1
                    },
                    "size": {
                        "type": "string",
                        "description": "Size of the item (small, medium, large)",
                        "enum": ["small", "medium", "large"],
                    },
                    "combo": {
                        "type": "boolean",
                        "description": "Whether this item is part of a combo",
                        "default": False
                    },
                    "combo_type": {
                        "type": "string",
                        "description": "Type of combo (regular_combo, large_combo)",
                        "enum": ["regular_combo", "large_combo"],
                    },
                    "customizations": {
                        "type": "array",
                        "description": "List of customizations for this item",
                        "items": {
                            "type": "string",
                            "enum": list(CUSTOMIZATIONS.keys()),
                        },
                    },
                    "protein": {
                        "type": "string",
                        "description": "Protein choice for applicable items",
                        "enum": list(PROTEIN_OPTIONS.keys()),
                    },
                    "drink_choice": {
                        "type": "string",
                        "description": "Drink choice for combos",
                        "enum": list(DRINK_OPTIONS.keys()),
                    }
                },
                "required": ["item_id"],
            },
        },
        "special_instructions": {
            "type": "string",
            "description": "Any special instructions for the entire order",
        },
        "action": {
            "type": "string",
            "description": "Action to take with this order: 'add_item' to add items to the current order, 'update_items' to update existing items (e.g., make them combos), 'confirm_order' to show order summary and ask for confirmation, 'finalize' to complete payment after customer confirms, 'new_order' to start a new order, or 'clear' to cancel the current order",
            "enum": ["add_item", "update_items", "confirm_order", "finalize", "new_order", "clear"],
            "default": "add_item"
        }
    },
    required=["items"],
)

async def process_food_order(params: FunctionCallParams):
    """
    Process a food order and return the order details.
    
    Args:
        params: Function call parameters containing the order details
        
    Returns:
        Order confirmation with details and total price
    """
    print("===== process_food_order function called =====")
    logger.info("===== process_food_order function called =====")
    print(f"Order parameters received: {json.dumps(params.arguments)}")
    logger.info(f"Order parameters received: {json.dumps(params.arguments)}")
    
    try:
        # Extract order items from the parameters
        arguments = params.arguments
        items = arguments.get("items", [])
        special_instructions = arguments.get("special_instructions", "")
        action = arguments.get("action", "add_item")
        
        # Handle different actions
        if action == "new_order":
            # Start a new order
            current_order_session.clear_order()
            current_order_session.start_new_order()
            print(f"Started new order with invoice ID: {current_order_session.current_invoice_id}")
            logger.info(f"Started new order with invoice ID: {current_order_session.current_invoice_id}")
            
            response = {
                "status": "new_order_started",
                "invoice_id": current_order_session.current_invoice_id,
                "message": "New order started successfully",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            await params.result_callback(response)
            return
            
        elif action == "clear":
            # Clear the current order
            invoice_id = current_order_session.current_invoice_id
            current_order_session.clear_order()
            print(f"Cleared order with invoice ID: {invoice_id}")
            logger.info(f"Cleared order with invoice ID: {invoice_id}")
            
            if WEBSOCKET_ENABLED:
                try:
                    await clear_order(invoice_id)
                except Exception as e:
                    print(f"Failed to clear order via WebSocket: {e}")
                    logger.error(f"Failed to clear order via WebSocket: {e}")
            
            response = {
                "status": "order_cleared",
                "message": "Order has been cleared",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            await params.result_callback(response)
            return
            
        elif action == "update_items":
            # Update existing items (e.g., make them combos) instead of adding new ones
            if not current_order_session.is_order_active or not current_order_session.current_order_items:
                response = {
                    "status": "error",
                    "message": "No active order to update",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                await params.result_callback(response)
                return
                
            # Update the items
            updated_items = []
            removed_items = []
            
            # Special handling for soda replacement scenario
            # If we have multiple soda items with drink_choice, this is likely a replacement request
            soda_items = [item for item in items if item.get("item_id") == "soda" and item.get("drink_choice")]
            if len(soda_items) > 1:
                # This is a soda replacement scenario - remove all existing sodas first
                items_to_remove = []
                for i, order_item in enumerate(current_order_session.current_order_items):
                    if order_item["item_id"] == "soda":
                        items_to_remove.append(i)
                
                # Remove existing sodas in reverse order
                for i in sorted(items_to_remove, reverse=True):
                    removed_item = current_order_session.current_order_items.pop(i)
                    removed_items.append(removed_item)
                    print(f"SODA REPLACEMENT: Removed {removed_item['description']}")
                    logger.info(f"SODA REPLACEMENT: Removed {removed_item['description']}")
                
                # Now add the new specific soda types
                for soda_item in soda_items:
                    # Convert drink_choice to specific soda type
                    corrected_item_id = detect_soda_type_conversion(
                        soda_item.get("item_id"), 
                        soda_item.get("drink_choice"), 
                        MENU_ITEMS
                    )
                    
                    # Create new soda item
                    new_soda = {
                        "item_id": corrected_item_id,
                        "quantity": soda_item.get("quantity", 1),
                        "size": soda_item.get("size", "regular"),
                        "combo": False,
                        "combo_type": None,
                        "customizations": [],
                        "protein": None,
                        "drink_choice": None,
                    }
                    
                    # Build description and calculate price
                    new_soda["description"] = rebuild_item_description(new_soda, MENU_ITEMS, SIZES, COMBOS, PROTEIN_OPTIONS)
                    new_soda["price"] = calculate_order_price([new_soda])
                    
                    # Add to order
                    current_order_session.current_order_items.append(new_soda)
                    updated_items.append(new_soda)
                    
                    print(f"SODA REPLACEMENT: Added {new_soda['description']}")
                    logger.info(f"SODA REPLACEMENT: Added {new_soda['description']}")
            else:
                # Regular update logic for non-soda-replacement scenarios
                for update_item in items:
                    item_id = update_item.get("item_id")
                    requested_quantity = update_item.get("quantity")
                    
                    # Check if this is a removal request (quantity 0 or explicit remove flag)
                    is_removal = (requested_quantity == 0 or update_item.get("remove", False))
                    
                    if is_removal:
                        # Find and remove items with matching item_id
                        items_to_remove = []
                        for i, order_item in enumerate(current_order_session.current_order_items):
                            if order_item["item_id"] == item_id:
                                items_to_remove.append(i)
                        
                        # Remove items in reverse order to avoid index issues
                        for i in sorted(items_to_remove, reverse=True):
                            removed_item = current_order_session.current_order_items.pop(i)
                            removed_items.append(removed_item)
                            print(f"REMOVED ITEM: {removed_item['description']}")
                            logger.info(f"REMOVED ITEM: {removed_item['description']}")
                    else:
                        # Generic approach for handling item updates and additions
                        found = False
                        for i, order_item in enumerate(current_order_session.current_order_items):
                            if order_item["item_id"] == item_id:
                                found = True
                                # Special case: if updating soda with drink_choice, convert to specific soda type
                                if item_id == "soda" and update_item.get("drink_choice"):
                                    corrected_item_id = detect_soda_type_conversion(item_id, update_item.get("drink_choice"), MENU_ITEMS)
                                    if corrected_item_id != item_id:
                                        current_order_session.current_order_items[i]["item_id"] = corrected_item_id
                                        # Remove drink_choice since it's now a specific item
                                        current_order_session.current_order_items[i]["drink_choice"] = None
                                        print(f"SODA CONVERSION: Converted {item_id} to {corrected_item_id}")
                                        logger.info(f"SODA CONVERSION: Converted {item_id} to {corrected_item_id}")
                                
                                # Update existing item
                                for key, value in update_item.items():
                                    if key != "item_id" and key != "drink_choice" and value is not None:
                                        current_order_session.current_order_items[i][key] = value
                                
                                # Special handling for combo conversion
                                if update_item.get("combo") and not current_order_session.current_order_items[i].get("combo_type"):
                                    # Set default combo type if combo is True but no combo_type specified
                                    current_order_session.current_order_items[i]["combo_type"] = get_default_combo_type(COMBOS)
                                    print(f"COMBO CONVERSION: Set default combo_type to {current_order_session.current_order_items[i]['combo_type']}")
                                    logger.info(f"COMBO CONVERSION: Set default combo_type to {current_order_session.current_order_items[i]['combo_type']}")
                                        
                                # Update description based on changes
                                if "size" in update_item or "combo" in update_item or "protein" in update_item or "customizations" in update_item or "quantity" in update_item or update_item.get("drink_choice"):
                                    # Rebuild description based on current properties
                                    current_order_session.current_order_items[i]["description"] = rebuild_item_description(
                                        current_order_session.current_order_items[i], 
                                        MENU_ITEMS, SIZES, COMBOS, PROTEIN_OPTIONS
                                    )
                                    
                                # Recalculate price based on current properties
                                current_order_session.current_order_items[i]["price"] = calculate_order_price([current_order_session.current_order_items[i]])
                                updated_items.append(current_order_session.current_order_items[i])
                                break
                        
                        # If item not found, add it as a new item
                        if not found:
                            new_item = create_new_item_from_update(update_item, MENU_ITEMS, SIZES, COMBOS, PROTEIN_OPTIONS)
                            if new_item:
                                current_order_session.current_order_items.append(new_item)
                                updated_items.append(new_item)
            
            # Calculate the total price for all items in the order
            total_price = sum(item["price"] for item in current_order_session.current_order_items)
            
            # Create the response
            response = {
                "invoice_id": current_order_session.current_invoice_id,
                "status": "items_updated",
                "items": [item["description"] for item in updated_items],
                "removed_items": [item["description"] for item in removed_items],
                "total_items": len(current_order_session.current_order_items),
                "total_price": total_price,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            print(f"Order response created: {json.dumps(response)}")
            logger.info(f"Order response created: {json.dumps(response)}")
            
            # Broadcast the order update to all connected WebSocket clients if WebSocket is enabled
            if WEBSOCKET_ENABLED:
                try:
                    print(f"WEBSOCKET_ENABLED is True, about to publish order update")
                    logger.info(f"WEBSOCKET_ENABLED is True, about to publish order update")
                    await publish_order_update(
                        current_order_session.current_invoice_id,
                        current_order_session.current_order_items
                    )
                    print(f"Order {current_order_session.current_invoice_id} update published to WebSocket clients")
                    logger.info(f"Order {current_order_session.current_invoice_id} update published to WebSocket clients")
                except Exception as e:
                    print(f"Failed to publish order update to WebSocket: {e}")
                    logger.error(f"Failed to publish order update to WebSocket: {e}")
            
            await params.result_callback(response)
            return
            
        elif action == "confirm_order":
            # Show order summary and ask for customer confirmation
            if not current_order_session.is_order_active or not current_order_session.current_order_items:
                response = {
                    "status": "error",
                    "message": "No active order to confirm",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                await params.result_callback(response)
                return
            
            # Calculate the total price for all items in the order
            total_price = sum(item["price"] for item in current_order_session.current_order_items)
            
            # Create order confirmation response
            response = {
                "invoice_id": current_order_session.current_invoice_id,
                "status": "order_confirmation",
                "items": [item["description"] for item in current_order_session.current_order_items],
                "total_items": len(current_order_session.current_order_items),
                "total_price": total_price,
                "message": "Please confirm your order. Say 'yes' to proceed with payment or 'no' to make changes.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            print(f"Order confirmation response: {json.dumps(response)}")
            logger.info(f"Order confirmation response: {json.dumps(response)}")
            
            # Broadcast the order confirmation to WebSocket clients
            if WEBSOCKET_ENABLED:
                try:
                    print(f"WEBSOCKET_ENABLED is True, about to publish order confirmation")
                    logger.info(f"WEBSOCKET_ENABLED is True, about to publish order confirmation")
                    
                    # Send order confirmation message
                    confirmation_message = {
                        "type": "order_confirmation",
                        "invoice_id": current_order_session.current_invoice_id,
                        "items": current_order_session.current_order_items,
                        "total_price": total_price,
                        "status": "awaiting_confirmation",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await publish_order_update(
                        current_order_session.current_invoice_id,
                        current_order_session.current_order_items,
                        "awaiting_confirmation"
                    )
                    print(f"Order confirmation published to WebSocket clients")
                    logger.info(f"Order confirmation published to WebSocket clients")
                except Exception as e:
                    print(f"Failed to publish order confirmation to WebSocket: {e}")
                    logger.error(f"Failed to publish order confirmation to WebSocket: {e}")
            
            await params.result_callback(response)
            return
            
        elif action == "finalize":
            # Finalize the current order with payment processing
            if not current_order_session.is_order_active or not current_order_session.current_order_items:
                response = {
                    "status": "error",
                    "message": "No active order to finalize",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                await params.result_callback(response)
                return
                
            # Add any new items if provided, but don't add duplicates or convert to combos here
            if items:
                process_items(items, special_instructions)
                
            # Finalize the order
            final_order = current_order_session.finalize_order()
            print(f"Finalized order: {json.dumps(final_order)}")
            logger.info(f"Finalized order: {json.dumps(final_order)}")
            
            # Step 1: Process payment (simulate payment processing)
            payment_response = {
                "status": "order_finalized",
                "invoice_id": final_order["invoice_id"],
                "items": [item["description"] for item in final_order["items"]],
                "total_price": final_order["total"],
                "payment_status": "processing",
                "message": "Processing payment... Please wait.",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            # Send payment processing response first
            await params.result_callback(payment_response)
            
            # IMPORTANT: Add a delay here to allow the agent to finish speaking
            # before showing the payment screen to the customer
            print(f"Waiting for agent to finish speaking before showing payment screen...")
            logger.info(f"Waiting for agent to finish speaking before showing payment screen...")
            
            # Wait 3 seconds to allow agent to finish speaking
            import asyncio
            await asyncio.sleep(3.0)
            
            # Step 2: Now broadcast the finalized order to show payment screen
            if WEBSOCKET_ENABLED:
                try:
                    await publish_final_order(final_order)
                    print(f"Final order published to WebSocket clients after delay")
                    logger.info(f"Final order published to WebSocket clients after delay")
                except Exception as e:
                    print(f"Failed to publish final order to WebSocket: {e}")
                    logger.error(f"Failed to publish final order to WebSocket: {e}")
            
            # Step 3: Simulate payment completion and clear order screen
            # In a real system, this would be triggered by payment gateway callback
            # For now, we'll send a follow-up message to clear the screen
            
            # Clear the order session for the next customer
            current_order_session.clear_order()
            print(f"Order session cleared for next customer")
            logger.info(f"Order session cleared for next customer")
            
            # Send order completion and screen clear message
            if WEBSOCKET_ENABLED:
                try:
                    # Send payment success and clear screen message
                    clear_message = {
                        "type": "payment_complete",
                        "invoice_id": final_order["invoice_id"],
                        "status": "payment_successful",
                        "message": "Payment successful! Thank you for your order.",
                        "clear_screen": True,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await clear_order(final_order["invoice_id"])
                    print(f"Order screen cleared for next customer")
                    logger.info(f"Order screen cleared for next customer")
                except Exception as e:
                    print(f"Failed to clear order screen: {e}")
                    logger.error(f"Failed to clear order screen: {e}")
            
            return
        
        # For add_item action or default behavior
        # If no active order, start a new one
        if not current_order_session.is_order_active:
            current_order_session.start_new_order()
            print(f"Started new order with invoice ID: {current_order_session.current_invoice_id}")
            logger.info(f"Started new order with invoice ID: {current_order_session.current_invoice_id}")
        
        # SMART DETECTION: Check if LLM is trying to modify existing items (combos, proteins, quantities, etc.)
        # If so, automatically treat this as an update_items action instead of add_item
        should_convert_to_update = False
        if current_order_session.is_order_active and current_order_session.current_order_items:
            for item in items:
                item_id = item.get("item_id")
                is_combo_request = normalize_combo_value(item.get("combo", False))
                has_protein = item.get("protein") is not None
                requested_quantity = item.get("quantity", 1)
                
                # SMART DETECTION: Check for soda type conversion
                if item_id == "soda" and item.get("drink_choice"):
                    corrected_item_id = detect_soda_type_conversion(item_id, item.get("drink_choice"), MENU_ITEMS)
                    if corrected_item_id != item_id:
                        print(f"SMART DETECTION: Converting soda with drink_choice '{item.get('drink_choice')}' to specific item '{corrected_item_id}'")
                        logger.info(f"SMART DETECTION: Converting soda with drink_choice '{item.get('drink_choice')}' to specific item '{corrected_item_id}'")
                        item["item_id"] = corrected_item_id
                        # Remove drink_choice since it's now a specific item
                        item.pop("drink_choice", None)
                        item_id = corrected_item_id
                
                # Check for invalid item IDs that represent valid conversion attempts
                corrected_item_id, suggested_protein = detect_invalid_item_id_patterns(
                    item_id, MENU_ITEMS, PROTEIN_OPTIONS
                )
                
                if corrected_item_id != item_id:
                    print(f"SMART DETECTION: Corrected invalid item_id '{item_id}' to '{corrected_item_id}'" + 
                          (f" with {suggested_protein} protein" if suggested_protein else ""))
                    logger.info(f"SMART DETECTION: Corrected invalid item_id '{item_id}' to '{corrected_item_id}'" + 
                               (f" with {suggested_protein} protein" if suggested_protein else ""))
                    
                    # Add suggested protein if not already specified
                    if suggested_protein and not has_protein:
                        item["protein"] = suggested_protein
                        has_protein = True
                
                # Find all variants of this item (e.g., chicken_burrito, burrito)
                item_variants = find_item_variants(corrected_item_id, MENU_ITEMS)
                
                # Check if this item already exists in the order (including related items)
                for existing_item in current_order_session.current_order_items:
                    existing_item_id = existing_item["item_id"]
                    existing_quantity = existing_item.get("quantity", 1)
                    requested_quantity = item.get("quantity", 1)
                    
                    # Check for direct match or variant match
                    item_matches = (existing_item_id == corrected_item_id or 
                                  existing_item_id in item_variants or 
                                  corrected_item_id in find_item_variants(existing_item_id, MENU_ITEMS))
                    
                    if item_matches:
                        print(f"SMART DETECTION: Detected item variant match - {existing_item_id} vs {corrected_item_id}")
                        logger.info(f"SMART DETECTION: Detected item variant match - {existing_item_id} vs {corrected_item_id}")
                        
                        # Update the item_id to the corrected one
                        item["item_id"] = corrected_item_id
                        
                        # PRIORITY 1: Check for combo conversion FIRST (before duplicate detection)
                        existing_combo = normalize_combo_value(existing_item.get("combo", False))
                        requested_combo = normalize_combo_value(item.get("combo", False))
                        
                        # Check for combo conversion - this takes priority over duplicate detection
                        if requested_combo and not existing_combo:
                            should_convert_to_update = True
                            print(f"SMART DETECTION: LLM trying to convert existing {existing_item_id} to combo, treating as update instead of add")
                            logger.info(f"SMART DETECTION: LLM trying to convert existing {existing_item_id} to combo, treating as update instead of add")
                            break
                        
                        # PRIORITY 2: Check for other modifications
                        # Check if combos match (both true or both false)
                        combo_matches = existing_combo == requested_combo
                        
                        # Check if customizations match
                        existing_customizations = set(existing_item.get("customizations", []))
                        requested_customizations = set(item.get("customizations", []))
                        customizations_match = existing_customizations == requested_customizations
                        
                        # Check if proteins match
                        proteins_match = existing_item.get("protein") == item.get("protein")
                        
                        # Check if sizes match (be flexible with None/regular equivalence)
                        existing_size = normalize_size_value(existing_item.get("size"))
                        requested_size = normalize_size_value(item.get("size"))
                        sizes_match = existing_size == requested_size
                        
                        # PRIORITY 3: Check for quantity modifications (only if no other changes detected)
                        # This should consolidate into existing items rather than creating new line items
                        # BUT: If quantity is 0, this is a removal request, not consolidation
                        # AND: If the requested quantity is different from existing, this might be a replacement
                        # IMPORTANT: Don't interfere with duplicate detection - only trigger when quantities differ
                        # SPECIAL CASE: If item has "action": "remove_item", this is an explicit removal request
                        
                        # Debug logging for matching conditions
                        print(f"SMART DETECTION DEBUG: combo_matches={combo_matches}, customizations_match={customizations_match}, proteins_match={proteins_match}, sizes_match={sizes_match}")
                        logger.info(f"SMART DETECTION DEBUG: combo_matches={combo_matches}, customizations_match={customizations_match}, proteins_match={proteins_match}, sizes_match={sizes_match}")
                        
                        if (combo_matches and customizations_match and proteins_match and sizes_match):
                            print(f"SMART DETECTION DEBUG: All conditions match, checking quantity logic")
                            logger.info(f"SMART DETECTION DEBUG: All conditions match, checking quantity logic")
                            
                            # Check for explicit removal action
                            if item.get("action") == "remove_item":
                                should_convert_to_update = True
                                print(f"SMART DETECTION: LLM trying to remove {requested_quantity} of {existing_item_id} (current: {existing_quantity}), treating as removal")
                                logger.info(f"SMART DETECTION: LLM trying to remove {requested_quantity} of {existing_item_id} (current: {existing_quantity}), treating as removal")
                                break
                            elif requested_quantity == 0:
                                should_convert_to_update = True
                                print(f"SMART DETECTION: LLM trying to remove {existing_item_id} by setting quantity to 0, treating as update instead of add")
                                logger.info(f"SMART DETECTION: LLM trying to remove {existing_item_id} by setting quantity to 0, treating as update instead of add")
                                break
                            else:
                                # CRITICAL FIX: When customer says "add one more X" and X already exists,
                                # this should ALWAYS be treated as quantity consolidation, not a new line item
                                should_convert_to_update = True
                                # Convert to additive quantity (existing + requested)
                                item["quantity"] = existing_quantity + requested_quantity
                                print(f"SMART DETECTION: LLM trying to add {requested_quantity} more {existing_item_id} (current: {existing_quantity}), consolidating to total quantity {item['quantity']}")
                                logger.info(f"SMART DETECTION: LLM trying to add {requested_quantity} more {existing_item_id} (current: {existing_quantity}), consolidating to total quantity {item['quantity']}")
                                break
                        
                        # Check for protein modification
                        if has_protein and existing_item.get("protein") != item.get("protein"):
                            should_convert_to_update = True
                            print(f"SMART DETECTION: LLM trying to modify existing {existing_item_id} protein to {item.get('protein')}, treating as update instead of add")
                            logger.info(f"SMART DETECTION: LLM trying to modify existing {existing_item_id} protein to {item.get('protein')}, treating as update instead of add")
                            break
                        
                        # Check for size modification
                        if item.get("size") and normalize_size_value(existing_item.get("size")) != normalize_size_value(item.get("size")):
                            should_convert_to_update = True
                            print(f"SMART DETECTION: LLM trying to modify existing {existing_item_id} size to {item.get('size')}, treating as update instead of add")
                            logger.info(f"SMART DETECTION: LLM trying to modify existing {existing_item_id} size to {item.get('size')}, treating as update instead of add")
                            break
                        
                        # Check for customization modification
                        if item.get("customizations") and existing_item.get("customizations") != item.get("customizations"):
                            should_convert_to_update = True
                            print(f"SMART DETECTION: LLM trying to modify existing {existing_item_id} customizations, treating as update instead of add")
                            logger.info(f"SMART DETECTION: LLM trying to modify existing {existing_item_id} customizations, treating as update instead of add")
                            break
                
                if should_convert_to_update:
                    break
        
        # If we detected a combo conversion attempt, handle it as an update
        if should_convert_to_update:
            # Update the items instead of adding new ones
            updated_items = []
            removed_items = []
            
            for update_item in items:
                item_id = update_item.get("item_id")
                requested_quantity = update_item.get("quantity", 1)
                
                # Check if this is a removal request (quantity 0 or explicit remove action)
                is_removal = (requested_quantity == 0 or update_item.get("action") == "remove_item")
                
                if is_removal:
                    # Handle removal requests
                    if update_item.get("action") == "remove_item" and requested_quantity > 0:
                        # This is a "remove X items" request, not "remove all items"
                        # Find the matching item and reduce its quantity
                        for i, order_item in enumerate(current_order_session.current_order_items):
                            if order_item["item_id"] == item_id:
                                current_quantity = order_item["quantity"]
                                new_quantity = max(0, current_quantity - requested_quantity)
                                
                                if new_quantity == 0:
                                    # Remove the entire item
                                    removed_item = current_order_session.current_order_items.pop(i)
                                    removed_items.append(removed_item)
                                    print(f"SMART CONVERSION: Removed entire item - {removed_item['description']}")
                                    logger.info(f"SMART CONVERSION: Removed entire item - {removed_item['description']}")
                                else:
                                    # Reduce the quantity
                                    current_order_session.current_order_items[i]["quantity"] = new_quantity
                                    
                                    # Update description and price
                                    current_order_session.current_order_items[i]["description"] = rebuild_item_description(
                                        current_order_session.current_order_items[i], 
                                        MENU_ITEMS, SIZES, COMBOS, PROTEIN_OPTIONS
                                    )
                                    current_order_session.current_order_items[i]["price"] = calculate_order_price([current_order_session.current_order_items[i]])
                                    updated_items.append(current_order_session.current_order_items[i])
                                    
                                    print(f"SMART CONVERSION: Reduced quantity - {current_order_session.current_order_items[i]['description']}")
                                    logger.info(f"SMART CONVERSION: Reduced quantity - {current_order_session.current_order_items[i]['description']}")
                                break
                    else:
                        # Remove all items with matching item_id (quantity 0)
                        items_to_remove = []
                        for i, order_item in enumerate(current_order_session.current_order_items):
                            if order_item["item_id"] == item_id:
                                items_to_remove.append(i)
                        
                        # Remove items in reverse order to avoid index issues
                        for i in sorted(items_to_remove, reverse=True):
                            removed_item = current_order_session.current_order_items.pop(i)
                            removed_items.append(removed_item)
                            print(f"SMART CONVERSION: Removed item - {removed_item['description']}")
                            logger.info(f"SMART CONVERSION: Removed item - {removed_item['description']}")
                else:
                    # Find all variants of this item for matching
                    item_variants = find_item_variants(item_id, MENU_ITEMS)
                    
                    # Find and update the existing item (including variants)
                    for i, order_item in enumerate(current_order_session.current_order_items):
                        existing_item_id = order_item["item_id"]
                        
                        # Check for direct match or variant match
                        item_matches = (existing_item_id == item_id or 
                                      existing_item_id in item_variants or 
                                      item_id in find_item_variants(existing_item_id, MENU_ITEMS))
                        
                        if item_matches:
                            print(f"SMART CONVERSION: Updating item variant - {existing_item_id} to {item_id}")
                            logger.info(f"SMART CONVERSION: Updating item variant - {existing_item_id} to {item_id}")
                            
                            # Check what type of update this is
                            is_combo_update = normalize_combo_value(update_item.get("combo", False)) and not normalize_combo_value(order_item.get("combo", False))
                            is_protein_update = update_item.get("protein") is not None and order_item.get("protein") != update_item.get("protein")
                            is_size_update = update_item.get("size") and normalize_size_value(order_item.get("size")) != normalize_size_value(update_item.get("size"))
                            is_customization_update = update_item.get("customizations") and order_item.get("customizations") != update_item.get("customizations")
                            is_quantity_update = update_item.get("quantity") and order_item.get("quantity") != update_item.get("quantity")
                            
                            # Only update if this is actually a modification we detected
                            if is_combo_update or is_protein_update or is_size_update or is_customization_update or is_quantity_update:
                                # Handle combo normalization - convert string combo values to boolean
                                if update_item.get("combo"):
                                    if isinstance(update_item["combo"], str):
                                        # If combo is a string like "regular_combo", convert to boolean and set combo_type
                                        current_order_session.current_order_items[i]["combo"] = True
                                        current_order_session.current_order_items[i]["combo_type"] = update_item["combo"]
                                        print(f"SMART CONVERSION: Normalized combo string '{update_item['combo']}' to combo=True, combo_type='{update_item['combo']}'")
                                        logger.info(f"SMART CONVERSION: Normalized combo string '{update_item['combo']}' to combo=True, combo_type='{update_item['combo']}'")
                                    else:
                                        current_order_session.current_order_items[i]["combo"] = True
                                        if update_item.get("combo_type"):
                                            current_order_session.current_order_items[i]["combo_type"] = update_item["combo_type"]
                                        elif not current_order_session.current_order_items[i].get("combo_type"):
                                            current_order_session.current_order_items[i]["combo_type"] = get_default_combo_type(COMBOS)
                                
                                # Update other properties
                                for key, value in update_item.items():
                                    if key not in ["item_id", "combo"] and value is not None:
                                        current_order_session.current_order_items[i][key] = value
                                
                                # If we're changing between item variants, update the item_id
                                if existing_item_id != item_id and item_id in MENU_ITEMS:
                                    current_order_session.current_order_items[i]["item_id"] = item_id
                                    print(f"SMART CONVERSION: Changed item_id from {existing_item_id} to {item_id}" + 
                                          (f" with {update_item.get('protein')} protein" if update_item.get('protein') else ""))
                                    logger.info(f"SMART CONVERSION: Changed item_id from {existing_item_id} to {item_id}" + 
                                               (f" with {update_item.get('protein')} protein" if update_item.get('protein') else ""))
                                        
                                # Update description based on changes
                                current_order_session.current_order_items[i]["description"] = rebuild_item_description(
                                    current_order_session.current_order_items[i], 
                                    MENU_ITEMS, SIZES, COMBOS, PROTEIN_OPTIONS
                                )
                                
                                # Recalculate price based on current properties
                                current_order_session.current_order_items[i]["price"] = calculate_order_price([current_order_session.current_order_items[i]])
                                updated_items.append(current_order_session.current_order_items[i])
                                break
            
            # Calculate the total price for all items in the order
            total_price = sum(item["price"] for item in current_order_session.current_order_items)
            
            # Create the response as an update
            response = {
                "invoice_id": current_order_session.current_invoice_id,
                "status": "items_updated",
                "items": [item["description"] for item in updated_items],
                "removed_items": [item["description"] for item in removed_items],
                "total_items": len(current_order_session.current_order_items),
                "total_price": total_price,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "smart_conversion": True,  # Flag to indicate this was automatically converted
            }
            
            print(f"SMART CONVERSION: Order response created: {json.dumps(response)}")
            logger.info(f"SMART CONVERSION: Order response created: {json.dumps(response)}")
            
            # Broadcast the order update to all connected WebSocket clients if WebSocket is enabled
            if WEBSOCKET_ENABLED:
                try:
                    print(f"WEBSOCKET_ENABLED is True, about to publish order update")
                    logger.info(f"WEBSOCKET_ENABLED is True, about to publish order update")
                    await publish_order_update(
                        current_order_session.current_invoice_id,
                        current_order_session.current_order_items
                    )
                    print(f"Order {current_order_session.current_invoice_id} update published to WebSocket clients")
                    logger.info(f"Order {current_order_session.current_invoice_id} update published to WebSocket clients")
                except Exception as e:
                    print(f"Failed to publish order update to WebSocket: {e}")
                    logger.error(f"Failed to publish order update to WebSocket: {e}")
            
            await params.result_callback(response)
            return
        
        # Process the items normally if no smart conversion is needed
        processed_items, duplicate_items = process_items(items, special_instructions)
        
        # Calculate the total price for all items in the order
        total_price = sum(item["price"] for item in current_order_session.current_order_items)
        
        # Create the response
        response = {
            "invoice_id": current_order_session.current_invoice_id,
            "status": "items_added",
            "items": [item["description"] for item in processed_items],
            "total_items": len(current_order_session.current_order_items),
            "total_price": total_price,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # Add information about duplicate handling if any duplicates were detected
        if duplicate_items:
            response["duplicate_handling"] = duplicate_items
        
        print(f"Order response created: {json.dumps(response)}")
        logger.info(f"Order response created: {json.dumps(response)}")
        
        # Add special instructions if provided
        if special_instructions:
            response["special_instructions"] = special_instructions
        
        # Broadcast the order update to all connected WebSocket clients if WebSocket is enabled
        if WEBSOCKET_ENABLED:
            try:
                print(f"WEBSOCKET_ENABLED is True, about to publish order update")
                logger.info(f"WEBSOCKET_ENABLED is True, about to publish order update")
                await publish_order_update(
                    current_order_session.current_invoice_id,
                    current_order_session.current_order_items
                )
                print(f"Order {current_order_session.current_invoice_id} update published to WebSocket clients")
                logger.info(f"Order {current_order_session.current_invoice_id} update published to WebSocket clients")
            except Exception as e:
                print(f"Failed to publish order update to WebSocket: {e}")
                logger.error(f"Failed to publish order update to WebSocket: {e}")
                import traceback
                print(traceback.format_exc())
                logger.error(traceback.format_exc())
        else:
            print("WEBSOCKET_ENABLED is False, order not published to WebSocket")
            logger.warning("WEBSOCKET_ENABLED is False, order not published to WebSocket")
        
        print(f"Sending order response back to LLM: {json.dumps(response)}")
        logger.info(f"Sending order response back to LLM: {json.dumps(response)}")
        await params.result_callback(response)
        print("===== process_food_order function completed =====")
        logger.info("===== process_food_order function completed =====")
        
    except Exception as e:
        print(f"Error processing food order: {e}")
        logger.error(f"Error processing food order: {e}")
        import traceback
        print(traceback.format_exc())
        logger.error(traceback.format_exc())
        await params.result_callback({
            "status": "error",
            "message": f"Failed to process your order: {str(e)}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

def process_items(items, special_instructions=""):
    """
    Process a list of items and add them to the current order session.
    
    Returns:
        tuple: (processed_items, duplicate_items)
        - processed_items: List of items that were processed
        - duplicate_items: List of items that were detected as duplicates and how they were handled
    """
    processed_items = []
    duplicate_items = []
    
    for item in items:
        item_id = item.get("item_id")
        if item_id in MENU_ITEMS:
            # Create a new item using our helper function
            processed_item = create_new_item_from_update(item, MENU_ITEMS, SIZES, COMBOS, PROTEIN_OPTIONS)
            
            if processed_item:
                # Add to the current order session with duplicate detection
                order_items, is_duplicate, action_taken = current_order_session.add_item_to_order(processed_item)
                
                if is_duplicate:
                    duplicate_info = {
                        "item": processed_item["description"],
                        "action_taken": action_taken,
                        "message": f"Detected potential duplicate order for {processed_item['description']}. " +
                                  (f"Increased quantity instead of adding duplicate." if action_taken == 'increased_quantity' else 
                                   "Added as new item.")
                    }
                    duplicate_items.append(duplicate_info)
                    logger.info(f"Duplicate handling: {json.dumps(duplicate_info)}")
                    
                    # If we increased the quantity of an existing item, we need to update our processed_items
                    # to reflect the item that was actually modified
                    if action_taken == 'increased_quantity':
                        # Find the item that was modified
                        for i, order_item in enumerate(current_order_session.current_order_items):
                            if (order_item["item_id"] == item_id and
                                order_item["size"] == processed_item["size"] and
                                order_item["protein"] == processed_item["protein"]):
                                processed_item = order_item
                                break
                
                processed_items.append(processed_item)
    
    return processed_items, duplicate_items
