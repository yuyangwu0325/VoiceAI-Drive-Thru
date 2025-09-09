"""
Test script specifically for the chicken burrito to beef burrito conversion issue.
This addresses the issue where asking to change chicken burrito to beef burrito creates a duplicate line.
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

class TestChickenToBeefBurritoFix(unittest.TestCase):
    """Test cases specifically for chicken burrito to beef burrito conversion."""
    
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
    
    def test_chicken_burrito_to_beef_burrito_conversion(self):
        """Test that changing chicken burrito to beef burrito updates existing item instead of adding new one."""
        # Step 1: Add a chicken burrito combo (simulating the exact scenario from logs)
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "chicken_burrito",
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
        self.assertAlmostEqual(add_params.result["total_price"], 11.97, places=2)  # Chicken burrito combo
        
        print(f"Step 1 - Added chicken burrito combo: ${add_params.result['total_price']}")
        
        # Step 2: LLM INCORRECTLY tries to add beef burrito (simulating the exact call from logs)
        wrong_params = MockFunctionCallParams({
            "items": [  # No action specified - defaults to add_item
                {
                    "item_id": "burrito",
                    "combo": "regular_combo",  # Note: LLM used string instead of boolean
                    "protein": "beef"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Verify the smart conversion worked
        self.assertEqual(wrong_params.result["status"], "items_updated")  # Should be updated, not added
        self.assertEqual(wrong_params.result["total_items"], 1)  # Should still be 1 item, not 2!
        self.assertTrue(wrong_params.result.get("smart_conversion", False))  # Should have smart conversion flag
        
        # Calculate expected price for beef burrito combo
        # Burrito: 7.99 + Beef: 0.75 + Fries: 2.99 + Soda: 1.99 - Discount: 1.50 = 12.22
        expected_price = 12.22
        self.assertAlmostEqual(wrong_params.result["total_price"], expected_price, places=2)
        
        print(f"Step 2 - Smart conversion to beef burrito combo: ${wrong_params.result['total_price']}")
        print(f"Items: {wrong_params.result['items']}")
        print(f"Smart conversion flag: {wrong_params.result.get('smart_conversion', False)}")
        
        # Verify the description shows it's a beef burrito combo
        self.assertIn("Beef", wrong_params.result["items"][0])
        self.assertIn("Regular Combo", wrong_params.result["items"][0])
        
        # Verify the backend order session has correct data
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        
        session_item = current_order_session.current_order_items[0]
        self.assertEqual(session_item["item_id"], "burrito")  # Should be changed to burrito
        self.assertEqual(session_item["protein"], "beef")
        self.assertTrue(session_item["combo"])
        self.assertEqual(session_item["combo_type"], "regular_combo")
        self.assertAlmostEqual(session_item["price"], expected_price, places=2)
        
        print(f"Backend session updated correctly: {session_item['description']}")
    
    def test_chicken_burrito_to_beef_burrito_no_combo(self):
        """Test changing chicken burrito to beef burrito without combo."""
        # Step 1: Add a regular chicken burrito
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "chicken_burrito",
                    "quantity": 1,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Step 2: Change to beef burrito
        change_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "burrito",
                    "protein": "beef"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(change_params))
        
        # Verify smart conversion
        self.assertEqual(change_params.result["status"], "items_updated")
        self.assertEqual(change_params.result["total_items"], 1)
        self.assertTrue(change_params.result.get("smart_conversion", False))
        
        # Expected: Regular burrito with beef = 7.99 + 0.75 = 8.74
        self.assertAlmostEqual(change_params.result["total_price"], 8.74, places=2)
        self.assertIn("with Beef", change_params.result["items"][0])

if __name__ == "__main__":
    unittest.main()
