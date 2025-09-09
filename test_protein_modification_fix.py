"""
Test script specifically for the protein modification fix.
This tests the scenario where LLM incorrectly adds a new item with protein instead of updating existing item.
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

class TestProteinModificationFix(unittest.TestCase):
    """Test cases for protein modification fix."""
    
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
    
    def test_taco_protein_modification_fixed(self):
        """Test that LLM's wrong protein modification is automatically fixed."""
        # Step 1: Add regular tacos
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "taco",
                    "quantity": 2,
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
        self.assertAlmostEqual(add_params.result["total_price"], 7.98, places=2)  # 2 * 3.99
        
        print(f"Step 1 - Added tacos: ${add_params.result['total_price']}")
        
        # Step 2: LLM INCORRECTLY tries to add taco with beef (no action specified, defaults to add_item)
        # This simulates the exact scenario from the logs
        wrong_params = MockFunctionCallParams({
            "items": [  # No action specified - defaults to add_item
                {
                    "item_id": "taco",
                    "quantity": 2,
                    "protein": "beef"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Verify the smart conversion worked
        self.assertEqual(wrong_params.result["status"], "items_updated")  # Should be updated, not added
        self.assertEqual(wrong_params.result["total_items"], 1)  # Should still be 1 item, not 2!
        self.assertTrue(wrong_params.result.get("smart_conversion", False))  # Should have smart conversion flag
        
        # Calculate expected price with beef protein
        # 2 tacos with beef: 2 * (3.99 + 0.75) = 2 * 4.74 = 9.48
        expected_price = 9.48
        self.assertAlmostEqual(wrong_params.result["total_price"], expected_price, places=2)
        
        print(f"Step 2 - Smart conversion to beef: ${wrong_params.result['total_price']}")
        print(f"Items: {wrong_params.result['items']}")
        print(f"Smart conversion flag: {wrong_params.result.get('smart_conversion', False)}")
        
        # Verify the description shows it has beef
        self.assertIn("with Beef", wrong_params.result["items"][0])
    
    def test_burrito_protein_modification_fixed(self):
        """Test smart conversion with burrito protein modification."""
        # Step 1: Add a regular burrito
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burrito",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Step 2: LLM incorrectly tries to add burrito with steak
        wrong_params = MockFunctionCallParams({
            "items": [  # No action - defaults to add_item
                {
                    "item_id": "burrito",
                    "protein": "steak"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Verify smart conversion
        self.assertEqual(wrong_params.result["status"], "items_updated")
        self.assertEqual(wrong_params.result["total_items"], 1)
        self.assertTrue(wrong_params.result.get("smart_conversion", False))
        
        # Should have steak protein with upgrade cost
        self.assertIn("with Steak", wrong_params.result["items"][0])
        # Large burrito (7.99 + 2.50) + steak upgrade (1.50) = 11.99
        self.assertAlmostEqual(wrong_params.result["total_price"], 11.99, places=2)
    
    def test_normal_add_item_still_works(self):
        """Test that normal add_item functionality still works when not a protein modification."""
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
        
        # Add a different item (should work normally)
        add_params2 = MockFunctionCallParams({
            "items": [  # No action - defaults to add_item
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
    
    def test_multiple_modifications_selective_smart_conversion(self):
        """Test smart conversion when multiple items exist and only one needs modification."""
        # Add multiple items
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "taco",
                    "quantity": 2,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                },
                {
                    "item_id": "burrito",
                    "quantity": 1,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # LLM tries to modify only the taco protein
        wrong_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "taco",
                    "protein": "beef"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Should smart convert only the taco
        self.assertEqual(wrong_params.result["status"], "items_updated")
        self.assertEqual(wrong_params.result["total_items"], 2)  # Still 2 items
        self.assertTrue(wrong_params.result.get("smart_conversion", False))
        
        # Only the taco should be modified
        self.assertIn("with Beef", wrong_params.result["items"][0])

if __name__ == "__main__":
    unittest.main()
