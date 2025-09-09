"""
Test script specifically for item removal functionality.
This addresses the issues found in the earlier tests where items weren't being properly removed.
"""

import unittest
import asyncio
import json
from food_ordering import process_food_order
from pipecat.services.llm_service import FunctionCallParams

# Create a mock FunctionCallParams class for testing
class MockFunctionCallParams:
    def __init__(self, arguments):
        self.arguments = arguments
        self.result = None
    
    async def result_callback(self, result):
        self.result = result

class TestItemRemoval(unittest.TestCase):
    """Test cases specifically for item removal functionality."""
    
    def setUp(self):
        """Set up for each test."""
        # Reset the current order session
        from food_ordering import current_order_session
        current_order_session.clear_order()
        
        # Create a new event loop for each test
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()
    
    def test_remove_single_item_from_order(self):
        """Test removing a single item from an order with multiple items."""
        # First add multiple items
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                },
                {
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": []
                },
                {
                    "item_id": "soda",
                    "quantity": 2,
                    "size": "small",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Verify we have 3 items
        self.assertEqual(add_params.result["total_items"], 3)
        initial_total = add_params.result["total_price"]
        
        # Now try to remove the fries using the "remove" action
        remove_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "fries",
                    "remove": True
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(remove_params))
        
        # Check the result - we should have 2 items left
        print(f"Remove result: {json.dumps(remove_params.result, indent=2)}")
        
        # The current implementation doesn't properly handle removal
        # Let's check what actually happens
        from food_ordering import current_order_session
        print(f"Current order items: {len(current_order_session.current_order_items)}")
        for item in current_order_session.current_order_items:
            print(f"  - {item['description']}")
    
    def test_remove_by_quantity_zero(self):
        """Test removing an item by setting its quantity to zero."""
        # First add multiple items
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                },
                {
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Verify we have 2 items
        self.assertEqual(add_params.result["total_items"], 2)
        
        # Now set the burger quantity to 0
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 0
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Check the result
        print(f"Update result: {json.dumps(update_params.result, indent=2)}")
        
        # Check what actually happens
        from food_ordering import current_order_session
        print(f"Current order items: {len(current_order_session.current_order_items)}")
        for item in current_order_session.current_order_items:
            print(f"  - {item['description']} (quantity: {item['quantity']})")

if __name__ == "__main__":
    unittest.main()
