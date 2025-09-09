#!/usr/bin/env python3
"""
Test script for "two fries and two soda" with existing order items.
"""

import asyncio
import json
from food_ordering import process_food_order
from pipecat.services.llm_service import FunctionCallParams

class MockFunctionCallParams:
    def __init__(self, arguments):
        self.arguments = arguments
        self.result = None
    
    async def result_callback(self, result):
        self.result = result

async def test_with_existing_order():
    """Test adding 'two fries and two soda' when there's already an existing order"""
    # Reset the current order session
    from food_ordering import current_order_session
    current_order_session.clear_order()
    
    print("=== Testing 'two fries and two soda' with existing order ===")
    
    # Step 1: Add a burger first
    print("Step 1: Adding a burger")
    params1 = MockFunctionCallParams({
        "action": "add_item",
        "items": [
            {
                "item_id": "burger",
                "quantity": 1,
                "size": "medium",
                "combo": False,
                "customizations": []
            }
        ]
    })
    
    try:
        await process_food_order(params1)
        print(f"✅ Burger added: {params1.result['status']}, Total: ${params1.result['total_price']}")
    except Exception as e:
        print(f"❌ Error adding burger: {e}")
        return
    
    # Step 2: Now add "two fries and two soda"
    print("Step 2: Adding two fries and two soda")
    params2 = MockFunctionCallParams({
        "action": "add_item",  # This might trigger Smart Detection if it thinks it's a duplicate
        "items": [
            {
                "item_id": "fries",
                "quantity": 2,
                "size": "regular",
                "combo": False,
                "customizations": []
            },
            {
                "item_id": "soda",
                "quantity": 2,
                "size": "regular",
                "combo": False,
                "customizations": []
            }
        ]
    })
    
    try:
        await process_food_order(params2)
        
        print(f"✅ SUCCESS: {params2.result['status']}")
        print(f"Total items: {params2.result['total_items']}")
        print(f"Total price: ${params2.result['total_price']}")
        print(f"Smart conversion: {params2.result.get('smart_conversion', False)}")
        print(f"Items added:")
        for item in params2.result['items']:
            print(f"  - {item}")
            
        # Check the backend state
        print(f"\nBackend order session:")
        print(f"  Active: {current_order_session.is_order_active}")
        print(f"  Items count: {len(current_order_session.current_order_items)}")
        for i, item in enumerate(current_order_session.current_order_items):
            print(f"  Item {i+1}: {item['description']} (quantity: {item['quantity']}, price: ${item['price']})")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        print(traceback.format_exc())

async def test_with_existing_fries():
    """Test adding 'two fries and two soda' when fries already exist (potential Smart Detection trigger)"""
    # Reset the current order session
    from food_ordering import current_order_session
    current_order_session.clear_order()
    
    print("\n=== Testing with existing fries (Smart Detection scenario) ===")
    
    # Step 1: Add one fries first
    print("Step 1: Adding one fries")
    params1 = MockFunctionCallParams({
        "action": "add_item",
        "items": [
            {
                "item_id": "fries",
                "quantity": 1,
                "size": "regular",
                "combo": False,
                "customizations": []
            }
        ]
    })
    
    try:
        await process_food_order(params1)
        print(f"✅ Fries added: {params1.result['status']}, Total: ${params1.result['total_price']}")
    except Exception as e:
        print(f"❌ Error adding fries: {e}")
        return
    
    # Step 2: Now try to add "two fries and two soda" - this might trigger Smart Detection
    print("Step 2: Adding two fries and two soda (might trigger Smart Detection)")
    params2 = MockFunctionCallParams({
        "items": [  # No action specified - defaults to add_item
            {
                "item_id": "fries",
                "quantity": 2,
                "size": "regular",
                "combo": False,
                "customizations": []
            },
            {
                "item_id": "soda",
                "quantity": 2,
                "size": "regular",
                "combo": False,
                "customizations": []
            }
        ]
    })
    
    try:
        await process_food_order(params2)
        
        print(f"Result: {params2.result['status']}")
        print(f"Total items: {params2.result['total_items']}")
        print(f"Total price: ${params2.result['total_price']}")
        print(f"Smart conversion: {params2.result.get('smart_conversion', False)}")
        
        if params2.result.get('smart_conversion'):
            print("⚠️  Smart Detection was triggered!")
            print("Items updated:")
            for item in params2.result.get('items', []):
                print(f"  - {item}")
        else:
            print("Items added:")
            for item in params2.result.get('items', []):
                print(f"  - {item}")
            
        # Check the backend state
        print(f"\nBackend order session:")
        print(f"  Items count: {len(current_order_session.current_order_items)}")
        for i, item in enumerate(current_order_session.current_order_items):
            print(f"  Item {i+1}: {item['description']} (quantity: {item['quantity']}, price: ${item['price']})")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    print("🧪 Testing 'two fries and two soda' in different scenarios...")
    asyncio.run(test_with_existing_order())
    asyncio.run(test_with_existing_fries())
