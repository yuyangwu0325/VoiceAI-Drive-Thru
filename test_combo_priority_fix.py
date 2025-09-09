"""
Test script to verify that combo conversion takes priority over duplicate detection.
This addresses the specific issue where "chicken burger combo" was being treated as a duplicate instead of a combo conversion.
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

class TestComboPriorityFix(unittest.TestCase):
    """Test cases to verify combo conversion takes priority over duplicate detection."""
    
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
    
    def test_chicken_burger_combo_conversion_priority(self):
        """Test that combo conversion takes priority over duplicate detection."""
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
        
        # Verify initial state
        self.assertEqual(add_params.result["status"], "items_added")
        self.assertEqual(add_params.result["total_items"], 1)
        self.assertAlmostEqual(add_params.result["total_price"], 6.49, places=2)  # Regular chicken burger
        
        print(f"Step 1 - Added chicken burger: ${add_params.result['total_price']}")
        
        # Step 2: Convert to combo (this was the problematic scenario)
        combo_params = MockFunctionCallParams({
            "items": [  # No action specified - defaults to add_item, should be smart converted
                {
                    "item_id": "chicken_burger",
                    "combo": True  # This should trigger combo conversion, NOT duplicate detection
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(combo_params))
        
        # Verify the smart conversion worked correctly
        self.assertEqual(combo_params.result["status"], "items_updated")  # Should be updated, not added
        self.assertEqual(combo_params.result["total_items"], 1)  # Should still be 1 item, not 2!
        self.assertTrue(combo_params.result.get("smart_conversion", False))  # Should have smart conversion flag
        
        # Calculate expected combo price:
        # Chicken burger: 6.49 + Fries: 2.99 + Soda: 1.99 - Discount: 1.50 = 9.97
        expected_combo_price = 9.97
        self.assertAlmostEqual(combo_params.result["total_price"], expected_combo_price, places=2)
        
        print(f"Step 2 - Smart conversion to combo: ${combo_params.result['total_price']}")
        print(f"Items: {combo_params.result['items']}")
        print(f"Smart conversion flag: {combo_params.result.get('smart_conversion', False)}")
        
        # Verify the description shows it's a combo
        self.assertIn("Regular Combo", combo_params.result["items"][0])
        
        # Verify the backend order session has correct data
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        
        session_item = current_order_session.current_order_items[0]
        self.assertEqual(session_item["item_id"], "chicken_burger")
        self.assertEqual(session_item["quantity"], 1)  # Should still be 1, not 2!
        self.assertTrue(session_item["combo"])
        self.assertEqual(session_item["combo_type"], "regular_combo")
        self.assertAlmostEqual(session_item["price"], expected_combo_price, places=2)
        
        print(f"Backend session updated correctly: {session_item['description']}")
    
    def test_burger_combo_conversion_priority(self):
        """Test combo conversion priority with regular burger."""
        # Step 1: Add a medium burger
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": ["extra_cheese"]
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Step 2: Convert to combo
        combo_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "burger",
                    "combo": True,
                    "combo_type": "large_combo"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(combo_params))
        
        # Verify smart conversion
        self.assertEqual(combo_params.result["status"], "items_updated")
        self.assertEqual(combo_params.result["total_items"], 1)
        self.assertTrue(combo_params.result.get("smart_conversion", False))
        
        # Should be a large combo with extra cheese
        self.assertIn("Large Combo", combo_params.result["items"][0])
        self.assertIn("Extra cheese", combo_params.result["items"][0])
        
        # Verify quantity is still 1
        from food_ordering import current_order_session
        self.assertEqual(current_order_session.current_order_items[0]["quantity"], 1)

if __name__ == "__main__":
    unittest.main()
