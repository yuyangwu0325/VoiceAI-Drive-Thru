"""
This file contains the fix for the issue with handling fries when updating or removing them.
"""

def remove_items_from_order(current_order_items, item_id, size=None):
    """
    Remove items from the order that match the given item_id and size.
    
    Args:
        current_order_items: List of current order items
        item_id: ID of the item to remove
        size: Size of the item to remove (optional)
        
    Returns:
        tuple: (updated_order_items, removed_items)
    """
    removed_items = []
    items_to_remove = []
    
    # Find all items that match the criteria
    for i, order_item in enumerate(current_order_items):
        if (order_item["item_id"] == item_id and 
            (size is None or order_item["size"] == size)):
            items_to_remove.append(i)
    
    # Remove items in reverse order to avoid index issues
    for i in sorted(items_to_remove, reverse=True):
        removed_item = current_order_items.pop(i)
        removed_items.append(removed_item)
    
    return current_order_items, removed_items
