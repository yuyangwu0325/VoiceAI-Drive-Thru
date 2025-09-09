"""
Customization Validator - Fixes contradictory order customizations
"""

def validate_and_fix_customizations(customizations, user_input=""):
    """
    Validate and fix contradictory customizations
    
    Args:
        customizations: List of customization strings
        user_input: Original user input for context
    
    Returns:
        Fixed list of customizations
    """
    if not customizations:
        return customizations
    
    print(f"VALIDATION: Checking customizations: {customizations}")
    
    # Define contradictory pairs
    contradictions = [
        ('no_cheese', 'extra_cheese'),
        ('no_onion', 'extra_onion'), 
        ('no_lettuce', 'extra_lettuce'),
        ('no_tomato', 'extra_tomato'),
        ('no_mayo', 'extra_mayo'),
        ('no_pickle', 'extra_pickle')
    ]
    
    fixed_customizations = customizations.copy()
    
    # Check for contradictions
    for no_item, extra_item in contradictions:
        if no_item in fixed_customizations and extra_item in fixed_customizations:
            print(f"CONTRADICTION DETECTED: {no_item} + {extra_item}")
            
            # Analyze user intent from original input
            user_lower = user_input.lower()
            
            # If user said "no X extra X", it's likely a speech recognition error
            # Keep the extra version as it's more specific
            if f"no {no_item.split('_')[1]} extra {extra_item.split('_')[1]}" in user_lower:
                fixed_customizations.remove(no_item)
                print(f"CONTRADICTION FIXED: Removed {no_item}, kept {extra_item} (speech error)")
            
            # If user clearly wants extra, remove the no version
            elif "extra" in user_lower and extra_item.split('_')[1] in user_lower:
                fixed_customizations.remove(no_item)
                print(f"CONTRADICTION FIXED: Removed {no_item}, kept {extra_item} (user wants extra)")
            
            # If user clearly wants none, remove the extra version
            elif "no" in user_lower and no_item.split('_')[1] in user_lower:
                fixed_customizations.remove(extra_item)
                print(f"CONTRADICTION FIXED: Removed {extra_item}, kept {no_item} (user wants none)")
            
            # Default: keep the extra version (more common request)
            else:
                fixed_customizations.remove(no_item)
                print(f"CONTRADICTION FIXED: Default resolution - kept {extra_item}")
    
    if fixed_customizations != customizations:
        print(f"CUSTOMIZATIONS FIXED: {customizations} → {fixed_customizations}")
    
    return fixed_customizations

def clean_speech_transcription(text):
    """
    Clean common speech recognition errors in food orders
    
    Args:
        text: Raw transcription text
    
    Returns:
        Cleaned text
    """
    if not text:
        return text
    
    print(f"CLEANING TRANSCRIPTION: {text}")
    
    # Common speech recognition errors in food orders
    corrections = {
        # Contradictory phrases
        'no cheese extra cheese': 'extra cheese',
        'no onion extra onion': 'extra onion',
        'no lettuce extra lettuce': 'extra lettuce',
        'with no cheese extra cheese': 'with extra cheese',
        'with no onion extra onion': 'with extra onion',
        
        # Common misheard words
        'no cheese and extra cheese': 'extra cheese',
        'no onions and extra onions': 'extra onions',
        'without cheese but extra cheese': 'extra cheese',
        
        # Redundant phrases
        'extra extra cheese': 'extra cheese',
        'no no onions': 'no onions',
    }
    
    cleaned_text = text.lower()
    
    for error, correction in corrections.items():
        if error in cleaned_text:
            cleaned_text = cleaned_text.replace(error, correction)
            print(f"TRANSCRIPTION CORRECTED: '{error}' → '{correction}'")
    
    # Restore original case for first letter
    if text and cleaned_text:
        cleaned_text = text[0] + cleaned_text[1:]
    
    return cleaned_text

def analyze_order_intent(user_input, existing_items):
    """
    Analyze if user wants to add new item or modify existing
    
    Args:
        user_input: User's voice input
        existing_items: Current items in order
    
    Returns:
        'add' or 'modify'
    """
    user_lower = user_input.lower()
    
    # Keywords that indicate adding new item
    add_keywords = [
        'another', 'second', 'also', 'add', 'plus', 'and',
        'can i have', 'i want', 'i need', 'give me'
    ]
    
    # Keywords that indicate modification
    modify_keywords = [
        'change', 'modify', 'update', 'make that', 'instead',
        'actually', 'correction', 'fix'
    ]
    
    add_score = sum(1 for keyword in add_keywords if keyword in user_lower)
    modify_score = sum(1 for keyword in modify_keywords if keyword in user_lower)
    
    print(f"INTENT ANALYSIS: add_score={add_score}, modify_score={modify_score}")
    
    if modify_score > add_score:
        return 'modify'
    else:
        return 'add'

# Test the validator
if __name__ == "__main__":
    # Test contradictory customizations
    test_cases = [
        (['no_cheese', 'extra_cheese'], "burger with no cheese extra cheese"),
        (['no_onion', 'extra_onion'], "no onion extra onion please"),
        (['extra_cheese'], "extra cheese only"),
        (['no_onion', 'extra_cheese'], "no onion and extra cheese"),
    ]
    
    for customizations, user_input in test_cases:
        print(f"\nTEST: {customizations} with input: '{user_input}'")
        fixed = validate_and_fix_customizations(customizations, user_input)
        print(f"RESULT: {fixed}")
