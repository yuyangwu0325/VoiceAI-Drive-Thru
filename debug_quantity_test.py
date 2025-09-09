#!/usr/bin/env python3

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

async def test():
    # Reset the current order session
    from food_ordering import current_order_session
    current_order_session.clear_order()
    
    # Step 1: Add a single taco combo with extra cheese
    add_params = MockFunctionCallParams({
        "action": "add_item",
        "items": [
            {
                "item_id": "taco",
                "quantity": 1,
                "size": "regular",
                "combo": True,
                "combo_type": "regular_combo",
                "customizations": ["extra_cheese"]
            }
        ]
    })
    
    await process_food_order(add_params)
    print(f"Step 1 result: {add_params.result['total_items']} items, ${add_params.result['total_price']}")
    
    # Step 2: Try to change to 2 tacos (simulating the exact scenario from logs)
    wrong_params = MockFunctionCallParams({
        "items": [  # No action specified - defaults to add_item
            {
                "item_id": "taco",
                "quantity": 2,
                "combo": True,  # Same combo status but no combo_type
                "customizations": ["extra_cheese"]  # Same customizations
            }
        ]
    })
    
    await process_food_order(wrong_params)
    print(f"Step 2 result: {wrong_params.result['status']} - {wrong_params.result['total_items']} items, ${wrong_params.result['total_price']}")
    print(f"Smart conversion: {wrong_params.result.get('smart_conversion', False)}")
    
    # Check the actual order session
    print(f"Actual order items: {len(current_order_session.current_order_items)}")
    for i, item in enumerate(current_order_session.current_order_items):
        print(f"  Item {i+1}: {item['description']} (quantity: {item['quantity']})")

if __name__ == "__main__":
    asyncio.run(test())
