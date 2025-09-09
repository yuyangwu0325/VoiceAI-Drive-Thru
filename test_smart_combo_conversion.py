"""
Test script specifically for the smart combo conversion fix.
This tests the scenario where LLM incorrectly uses add_item instead of update_items for combo conversion.
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

class TestSmartComboConversion(unittest.TestCase):
    """Test cases for smart combo conversion fix."""
    
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
    
    def test_llm_wrong_combo_conversion_fixed(self):
        """Test that LLM's wrong combo conversion is automatically fixed."""
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
        
        # Verify initial state
        self.assertEqual(add_params.result["status"], "items_added")
        self.assertEqual(add_params.result["total_items"], 1)
        self.assertAlmostEqual(add_params.result["total_price"], 8.49, places=2)
        
        print(f"Step 1 - Added chicken burrito: ${add_params.result['total_price']}")
        
        # Step 2: LLM INCORRECTLY tries to add combo (no action specified, defaults to add_item)
        # This simulates the exact scenario from the logs
        wrong_params = MockFunctionCallParams({
            "items": [  # No action specified - defaults to add_item
                {
                    "item_id": "chicken_burrito",
                    "combo": True
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Verify the smart conversion worked
        self.assertEqual(wrong_params.result["status"], "items_updated")  # Should be updated, not added
        self.assertEqual(wrong_params.result["total_items"], 1)  # Should still be 1 item, not 2!
        self.assertTrue(wrong_params.result.get("smart_conversion", False))  # Should have smart conversion flag
        
        # Calculate expected combo price:
        # Chicken burrito: 8.49 + Fries: 2.99 + Soda: 1.99 - Discount: 1.50 = 11.97
        expected_combo_price = 11.97
        self.assertAlmostEqual(wrong_params.result["total_price"], expected_combo_price, places=2)
        
        print(f"Step 2 - Smart conversion to combo: ${wrong_params.result['total_price']}")
        print(f"Items: {wrong_params.result['items']}")
        print(f"Smart conversion flag: {wrong_params.result.get('smart_conversion', False)}")
        
        # Verify the description shows it's a combo
        self.assertIn("Regular Combo", wrong_params.result["items"][0])
    
    def test_llm_wrong_burger_combo_conversion_fixed(self):
        """Test smart conversion with burger."""
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
        
        # Step 2: LLM incorrectly tries to add combo
        wrong_params = MockFunctionCallParams({
            "items": [  # No action - defaults to add_item
                {
                    "item_id": "burger",
                    "combo": True,
                    "combo_type": "large_combo"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Verify smart conversion
        self.assertEqual(wrong_params.result["status"], "items_updated")
        self.assertEqual(wrong_params.result["total_items"], 1)
        self.assertTrue(wrong_params.result.get("smart_conversion", False))
        
        # Should be a large combo with extra cheese
        self.assertIn("Large Combo", wrong_params.result["items"][0])
        self.assertIn("Extra cheese", wrong_params.result["items"][0])
    
    def test_normal_add_item_still_works(self):
        """Test that normal add_item functionality still works when not a combo conversion."""
        # Add a burger
        add_params1 = MockFunctionCallParams({
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
        
        self.loop.run_until_complete(process_food_order(add_params1))
        
        # Add a different item (should work normally)
        add_params2 = MockFunctionCallParams({
            "items": [  # No action - defaults to add_item
                {
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params2))
        
        # Should add normally, not trigger smart conversion
        self.assertEqual(add_params2.result["status"], "items_added")
        self.assertEqual(add_params2.result["total_items"], 2)
        self.assertFalse(add_params2.result.get("smart_conversion", False))
    
    def test_multiple_items_selective_smart_conversion(self):
        """Test smart conversion when multiple items exist."""
        # Add multiple items
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
                    "item_id": "chicken_burrito",
                    "quantity": 1,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # LLM tries to make only the burger a combo
        wrong_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "burger",
                    "combo": True,
                    "combo_type": "regular_combo"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Should smart convert only the burger
        self.assertEqual(wrong_params.result["status"], "items_updated")
        self.assertEqual(wrong_params.result["total_items"], 2)  # Still 2 items
        self.assertTrue(wrong_params.result.get("smart_conversion", False))
        
        # Only the burger should be converted to combo
        self.assertIn("Regular Combo", wrong_params.result["items"][0])

if __name__ == "__main__":
    unittest.main()
