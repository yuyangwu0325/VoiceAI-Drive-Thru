"""
Test script specifically for the chicken burrito removal fix.
This addresses the issue where removing one item from a quantity of 2 creates incorrect order state.
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

class TestChickenBurritoRemovalFix(unittest.TestCase):
    """Test cases specifically for chicken burrito removal fix."""
    
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
    
    def test_remove_one_from_quantity_two(self):
        """Test removing one item from a quantity of 2."""
        # Step 1: Add 2 chicken burrito combos
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "chicken_burrito",
                    "quantity": 2,
                    "size": "regular",
                    "combo": True,
                    "combo_type": "regular_combo",
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Verify initial state
        self.assertEqual(add_params.result["status"], "items_added")
        self.assertEqual(add_params.result["total_items"], 1)  # 1 line item with quantity 2
        expected_initial_price = 2 * 11.97  # 2 chicken burrito combos
        self.assertAlmostEqual(add_params.result["total_price"], expected_initial_price, places=2)
        
        print(f"Step 1 - Added 2 chicken burrito combos: ${add_params.result['total_price']}")
        
        # Verify backend state
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        self.assertEqual(current_order_session.current_order_items[0]["quantity"], 2)
        
        # Step 2: Remove 1 chicken burrito (simulating the exact LLM call from logs)
        remove_params = MockFunctionCallParams({
            "items": [  # No action specified - should be smart converted
                {
                    "item_id": "chicken_burrito",
                    "quantity": 1,
                    "combo": True,
                    "action": "remove_item"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(remove_params))
        
        # Verify the smart conversion worked correctly
        self.assertEqual(remove_params.result["status"], "items_updated")
        self.assertEqual(remove_params.result["total_items"], 1)  # Should still be 1 line item
        self.assertTrue(remove_params.result.get("smart_conversion", False))
        
        # Should now have quantity 1 with price for 1 combo
        expected_final_price = 11.97  # 1 chicken burrito combo
        self.assertAlmostEqual(remove_params.result["total_price"], expected_final_price, places=2)
        
        print(f"Step 2 - Removed 1, left with 1: ${remove_params.result['total_price']}")
        print(f"Items: {remove_params.result['items']}")
        print(f"Smart conversion flag: {remove_params.result.get('smart_conversion', False)}")
        
        # Verify the backend order session has correct data
        self.assertEqual(len(current_order_session.current_order_items), 1)
        
        session_item = current_order_session.current_order_items[0]
        self.assertEqual(session_item["item_id"], "chicken_burrito")
        self.assertEqual(session_item["quantity"], 1)  # Should be reduced to 1
        self.assertTrue(session_item["combo"])
        self.assertEqual(session_item["combo_type"], "regular_combo")
        self.assertAlmostEqual(session_item["price"], expected_final_price, places=2)
        
        # Verify description shows quantity 1
        self.assertIn("1x", session_item["description"])
        self.assertIn("Regular Combo", session_item["description"])
        
        print(f"Backend session updated correctly: {session_item['description']}")
    
    def test_remove_all_from_quantity_two(self):
        """Test removing all items when quantity is 2."""
        # Step 1: Add 2 chicken burrito combos
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "chicken_burrito",
                    "quantity": 2,
                    "size": "regular",
                    "combo": True,
                    "combo_type": "regular_combo",
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Step 2: Remove 2 chicken burritos (remove all)
        remove_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "chicken_burrito",
                    "quantity": 2,
                    "combo": True,
                    "action": "remove_item"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(remove_params))
        
        # Should remove the entire item
        self.assertEqual(remove_params.result["status"], "items_updated")
        self.assertEqual(remove_params.result["total_items"], 0)  # No items left
        self.assertEqual(remove_params.result["total_price"], 0)
        self.assertTrue(remove_params.result.get("smart_conversion", False))
        
        # Verify backend
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 0)

if __name__ == "__main__":
    unittest.main()
