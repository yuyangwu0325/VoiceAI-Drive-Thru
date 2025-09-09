#!/usr/bin/env python3
"""
Test script specifically for the "two fries and two soda" issue.
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

async def test_two_fries_two_soda():
    """Test the specific scenario: 'two fries and two soda'"""
    # Reset the current order session
    from food_ordering import current_order_session
    current_order_session.clear_order()
    
    print("=== Testing 'two fries and two soda' scenario ===")
    
    # Test the exact scenario that's failing
    params = MockFunctionCallParams({
        "action": "add_item",
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
        await process_food_order(params)
        
        print(f"✅ SUCCESS: {params.result['status']}")
        print(f"Total items: {params.result['total_items']}")
        print(f"Total price: ${params.result['total_price']}")
        print(f"Items:")
        for item in params.result['items']:
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

async def test_step_by_step():
    """Test adding fries and soda step by step to isolate the issue"""
    # Reset the current order session
    from food_ordering import current_order_session
    current_order_session.clear_order()
    
    print("\n=== Testing step by step ===")
    
    # Step 1: Add two fries
    print("Step 1: Adding two fries")
    params1 = MockFunctionCallParams({
        "action": "add_item",
        "items": [
            {
                "item_id": "fries",
                "quantity": 2,
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
    
    # Step 2: Add two sodas
    print("Step 2: Adding two sodas")
    params2 = MockFunctionCallParams({
        "action": "add_item",
        "items": [
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
        print(f"✅ Sodas added: {params2.result['status']}, Total: ${params2.result['total_price']}")
        
        # Check final state
        print(f"\nFinal state:")
        print(f"  Total items: {params2.result['total_items']}")
        print(f"  Total price: ${params2.result['total_price']}")
        for item in params2.result['items']:
            print(f"  - {item}")
            
    except Exception as e:
        print(f"❌ Error adding sodas: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    print("🧪 Testing 'two fries and two soda' issue...")
    asyncio.run(test_two_fries_two_soda())
    asyncio.run(test_step_by_step())
