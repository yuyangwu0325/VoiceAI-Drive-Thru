"""
Test script specifically for the chicken burger quantity replacement fix.
This addresses the issue where asking to change "1 chicken burger combo" to "2 chicken burger combo" 
incorrectly adds items instead of replacing the quantity.
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

class TestChickenBurgerFix(unittest.TestCase):
    """Test cases specifically for chicken burger quantity replacement fix."""
    
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
    
    def test_chicken_burger_quantity_replacement(self):
        """Test that changing quantity replaces instead of adding."""
        # Step 1: Add 1 chicken burger combo
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "chicken_burger",
                    "quantity": 1,
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
        self.assertEqual(add_params.result["total_items"], 1)
        initial_price = add_params.result["total_price"]
        
        print(f"Step 1 - Added 1 chicken burger combo: ${initial_price}")
        
        # Step 2: Customer says "make it two chicken burger combo" (simulating the exact LLM call from logs)
        # LLM incorrectly uses string for combo instead of boolean
        change_params = MockFunctionCallParams({
            "items": [  # No action specified - defaults to add_item, should be smart converted
                {
                    "item_id": "chicken_burger",
                    "quantity": 2,
                    "combo": "regular_combo"  # LLM uses string instead of boolean
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(change_params))
        
        # Verify the smart conversion worked correctly
        self.assertEqual(change_params.result["status"], "items_updated")  # Should be updated, not added
        self.assertEqual(change_params.result["total_items"], 1)  # Should still be 1 item, not 2!
        self.assertTrue(change_params.result.get("smart_conversion", False))  # Should have smart conversion flag
        
        # Calculate expected price for 2 chicken burger combos
        # 2x Chicken Burger Regular Combo = 2 * 9.97 = 19.94
        expected_price = 19.94
        self.assertAlmostEqual(change_params.result["total_price"], expected_price, places=2)
        
        print(f"Step 2 - Smart conversion to 2 chicken burger combos: ${change_params.result['total_price']}")
        print(f"Items: {change_params.result['items']}")
        print(f"Smart conversion flag: {change_params.result.get('smart_conversion', False)}")
        
        # Verify the description shows it's 2 combos
        self.assertIn("2x", change_params.result["items"][0])
        self.assertIn("Regular Combo", change_params.result["items"][0])
        
        # Verify the backend order session has correct data
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        
        session_item = current_order_session.current_order_items[0]
        self.assertEqual(session_item["item_id"], "chicken_burger")
        self.assertEqual(session_item["quantity"], 2)  # Should be updated to 2
        self.assertTrue(session_item["combo"])
        self.assertEqual(session_item["combo_type"], "regular_combo")
        self.assertAlmostEqual(session_item["price"], expected_price, places=2)
        
        print(f"Backend session updated correctly: {session_item['description']}")
    
    def test_combo_string_normalization(self):
        """Test that combo string values are properly normalized to boolean."""
        # Step 1: Add a regular chicken burger
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "chicken_burger",
                    "quantity": 1,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Step 2: Convert to combo using string value (simulating LLM behavior)
        combo_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "chicken_burger",
                    "combo": "regular_combo"  # String instead of boolean
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(combo_params))
        
        # Verify smart conversion
        self.assertEqual(combo_params.result["status"], "items_updated")
        self.assertEqual(combo_params.result["total_items"], 1)
        self.assertTrue(combo_params.result.get("smart_conversion", False))
        
        # Should be a combo now
        self.assertIn("Regular Combo", combo_params.result["items"][0])
        
        # Check backend
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        session_item = current_order_session.current_order_items[0]
        self.assertTrue(session_item["combo"])  # Should be boolean True
        self.assertEqual(session_item["combo_type"], "regular_combo")

if __name__ == "__main__":
    unittest.main()
