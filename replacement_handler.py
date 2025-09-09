"""
Replacement Handler - Detects and handles item replacement requests
"""

def detect_replacement_intent(user_input: str, items: list) -> dict:
    """
    Detect if user wants to replace an item instead of adding it
    
    Args:
        user_input: The user's voice input
        items: List of items being processed
        
    Returns:
        Dict with replacement info: {
            'is_replacement': bool,
            'replacement_type': str,
            'target_item': str,
            'new_item': str
        }
    """
    if not user_input or not items:
        return {'is_replacement': False}
    
    user_lower = user_input.lower()
    
    # Replacement keywords
    replacement_keywords = [
        'instead', 'change that to', 'make that', 'switch to', 
        'change to', 'replace with', 'actually make it',
        'can you make that', 'make it a', 'change it to'
    ]
    
    # Check if any replacement keywords are present
    has_replacement_keyword = any(keyword in user_lower for keyword in replacement_keywords)
    
    if not has_replacement_keyword:
        return {'is_replacement': False}
    
    # Determine what type of replacement
    if len(items) == 1:
        item = items[0]
        item_id = item.get('item_id', '')
        
        # Common replacement patterns
        replacement_patterns = {
            'protein_change': ['chicken', 'beef', 'veggie'],
            'item_type_change': ['burger', 'taco', 'burrito', 'quesadilla'],
            'size_change': ['small', 'medium', 'large'],
            'combo_change': ['combo', 'meal']
        }
        
        # Detect type of replacement
        for pattern_type, keywords in replacement_patterns.items():
            if any(keyword in user_lower for keyword in keywords):
                return {
                    'is_replacement': True,
                    'replacement_type': pattern_type,
                    'target_item': 'last_item',  # Replace the most recent item
                    'new_item': item_id,
                    'keywords_found': [kw for kw in keywords if kw in user_lower]
                }
    
    return {
        'is_replacement': True,
        'replacement_type': 'general',
        'target_item': 'last_item',
        'new_item': items[0].get('item_id', '') if items else '',
        'keywords_found': [kw for kw in replacement_keywords if kw in user_lower]
    }

def should_replace_instead_of_update(user_input: str, items: list, existing_items: list) -> bool:
    """
    Determine if this should be a replacement instead of an update
    
    Args:
        user_input: User's voice input
        items: Items being processed
        existing_items: Current order items
        
    Returns:
        True if this should replace an item, False if it should update
    """
    replacement_info = detect_replacement_intent(user_input, items)
    
    if not replacement_info['is_replacement']:
        return False
    
    # If user says "instead" or similar, it's definitely a replacement
    strong_replacement_keywords = ['instead', 'change that to', 'replace with', 'actually make it']
    user_lower = user_input.lower()
    
    if any(keyword in user_lower for keyword in strong_replacement_keywords):
        return True
    
    # If changing item type (burger -> chicken burger), it's likely a replacement
    if replacement_info['replacement_type'] == 'item_type_change':
        return True
    
    return False

def find_item_to_replace(existing_items: list, replacement_info: dict) -> int:
    """
    Find which item in the order should be replaced
    
    Args:
        existing_items: Current order items
        replacement_info: Replacement information
        
    Returns:
        Index of item to replace, or -1 if not found
    """
    if not existing_items:
        return -1
    
    target_item = replacement_info.get('target_item', 'last_item')
    
    # If target_item is 'last_item', replace the most recent item
    if target_item == 'last_item':
        return len(existing_items) - 1
    
    # If target_item is a specific item_id, find it
    if isinstance(target_item, str) and target_item != 'last_item':
        for i, item in enumerate(existing_items):
            if item.get('item_id') == target_item:
                return i
    
    # Fallback: replace the last item
    return len(existing_items) - 1

def execute_replacement(existing_items: list, item_index: int, new_item: dict) -> dict:
    """
    Execute the replacement of an item
    
    Args:
        existing_items: Current order items
        item_index: Index of item to replace
        new_item: New item data
        
    Returns:
        Dict with replacement result
    """
    if item_index < 0 or item_index >= len(existing_items):
        return {'success': False, 'error': 'Invalid item index'}
    
    old_item = existing_items[item_index].copy()
    
    # Replace the item while preserving some properties
    existing_items[item_index].update({
        'item_id': new_item.get('item_id'),
        'customizations': new_item.get('customizations', old_item.get('customizations', [])),
        'protein': new_item.get('protein', old_item.get('protein')),
        'size': new_item.get('size', old_item.get('size', 'regular')),
        'combo': new_item.get('combo', old_item.get('combo', False)),
        'combo_type': new_item.get('combo_type', old_item.get('combo_type')),
        'drink_choice': new_item.get('drink_choice', old_item.get('drink_choice'))
    })
    
    return {
        'success': True,
        'old_item': old_item,
        'new_item': existing_items[item_index],
        'replaced_index': item_index
    }

# Test the replacement detection
if __name__ == "__main__":
    test_cases = [
        {
            'input': "can you make that as like a chicken burger instead",
            'items': [{'item_id': 'chicken_burger'}],
            'expected': True
        },
        {
            'input': "change that to a veggie burger",
            'items': [{'item_id': 'veggie_burger'}],
            'expected': True
        },
        {
            'input': "make it a combo",
            'items': [{'item_id': 'burger', 'combo': True}],
            'expected': False  # This is an update, not replacement
        },
        {
            'input': "add fries to that",
            'items': [{'item_id': 'fries'}],
            'expected': False  # This is adding, not replacing
        }
    ]
    
    for i, test in enumerate(test_cases):
        result = should_replace_instead_of_update(test['input'], test['items'], [])
        status = "✅" if result == test['expected'] else "❌"
        print(f"Test {i+1}: {status}")
        print(f"  Input: {test['input']}")
        print(f"  Expected: {test['expected']}, Got: {result}")
        
        replacement_info = detect_replacement_intent(test['input'], test['items'])
        print(f"  Replacement Info: {replacement_info}")
        print("---")
