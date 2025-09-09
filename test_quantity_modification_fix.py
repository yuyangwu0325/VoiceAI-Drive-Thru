"""
Test script specifically for the quantity modification fix.
This addresses the issue where asking to "make it two tacos" creates a duplicate line instead of updating quantity.
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

class TestQuantityModificationFix(unittest.TestCase):
    """Test cases specifically for quantity modification fix."""
    
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
    
    def test_taco_quantity_modification_fixed(self):
        """Test that asking to 'make it two tacos' updates quantity instead of adding new line."""
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
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Verify initial state
        self.assertEqual(add_params.result["status"], "items_added")
        self.assertEqual(add_params.result["total_items"], 1)
        # 1x Regular Taco Regular Combo with extra cheese
        # Taco: 3.99 + Extra cheese: 0.75 + Fries: 2.99 + Soda: 1.99 - Discount: 1.50 = 8.22
        self.assertAlmostEqual(add_params.result["total_price"], 8.22, places=2)
        
        print(f"Step 1 - Added 1x taco combo with extra cheese: ${add_params.result['total_price']}")
        
        # Step 2: LLM INCORRECTLY tries to add 2 tacos (simulating "make it two tacos")
        # This should be detected as a quantity update, not a new line item
        wrong_params = MockFunctionCallParams({
            "items": [  # No action specified - defaults to add_item, but should be smart converted
                {
                    "item_id": "taco",
                    "quantity": 2,
                    "combo": True,  # Same combo status
                    "customizations": ["extra_cheese"]  # Same customizations
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Verify the smart conversion worked
        self.assertEqual(wrong_params.result["status"], "items_updated")  # Should be updated, not added
        self.assertEqual(wrong_params.result["total_items"], 1)  # Should still be 1 item, not 2!
        self.assertTrue(wrong_params.result.get("smart_conversion", False))  # Should have smart conversion flag
        
        # Calculate expected price for 2 tacos with same specifications
        # 2x Regular Taco Regular Combo with extra cheese
        # Current pricing: 2 × (1x Regular Taco Regular Combo with extra cheese)
        # 1x combo = 8.22, so 2x combo = 16.44
        expected_price = 16.44
        self.assertAlmostEqual(wrong_params.result["total_price"], expected_price, places=2)
        
        print(f"Step 2 - Smart conversion to 2x tacos: ${wrong_params.result['total_price']}")
        print(f"Items: {wrong_params.result['items']}")
        print(f"Smart conversion flag: {wrong_params.result.get('smart_conversion', False)}")
        
        # Verify the description shows it's 2 tacos
        self.assertIn("2x", wrong_params.result["items"][0])
        self.assertIn("Regular Combo", wrong_params.result["items"][0])
        self.assertIn("Extra cheese", wrong_params.result["items"][0])
        
        # Verify the backend order session has correct data
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        
        session_item = current_order_session.current_order_items[0]
        self.assertEqual(session_item["item_id"], "taco")
        self.assertEqual(session_item["quantity"], 2)  # Should be updated to 2
        self.assertTrue(session_item["combo"])
        self.assertEqual(session_item["combo_type"], "regular_combo")
        self.assertIn("extra_cheese", session_item["customizations"])
        self.assertAlmostEqual(session_item["price"], expected_price, places=2)
        
        print(f"Backend session updated correctly: {session_item['description']}")
    
    def test_burger_quantity_modification_fixed(self):
        """Test quantity modification with burgers."""
        # Step 1: Add a medium burger
        add_params = MockFunctionCallParams({
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
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Step 2: Ask for 3 burgers with same specifications
        change_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 3,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(change_params))
        
        # Verify smart conversion
        self.assertEqual(change_params.result["status"], "items_updated")
        self.assertEqual(change_params.result["total_items"], 1)
        self.assertTrue(change_params.result.get("smart_conversion", False))
        
        # Expected: 3x Medium Burger = 3 * (5.99 + 1.50) = 3 * 7.49 = 22.47
        self.assertAlmostEqual(change_params.result["total_price"], 22.47, places=2)
        self.assertIn("3x", change_params.result["items"][0])
    
    def test_normal_add_different_item_still_works(self):
        """Test that adding a different item still works normally."""
        # Add a taco
        add_params1 = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "taco",
                    "quantity": 1,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params1))
        
        # Add a different item (burger) - should work normally
        add_params2 = MockFunctionCallParams({
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
        
        self.loop.run_until_complete(process_food_order(add_params2))
        
        # Should add normally, not trigger smart conversion
        self.assertEqual(add_params2.result["status"], "items_added")
        self.assertEqual(add_params2.result["total_items"], 2)
        self.assertFalse(add_params2.result.get("smart_conversion", False))

if __name__ == "__main__":
    unittest.main()
