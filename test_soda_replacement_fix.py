"""
Test script specifically for the soda replacement fix.
This addresses the issue where asking to change "3 sodas" to "2 coke and 1 lemonade" doesn't work properly.
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

class TestSodaReplacementFix(unittest.TestCase):
    """Test cases specifically for soda replacement fix."""
    
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
    
    def test_soda_replacement_scenario(self):
        """Test the exact scenario from the logs: 3 sodas -> 2 coke and 1 lemonade."""
        # Step 1: Add 3 sodas
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "soda",
                    "quantity": 3,
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
        self.assertAlmostEqual(add_params.result["total_price"], 5.97, places=2)  # 3 * 1.99
        
        print(f"Step 1 - Added 3 sodas: ${add_params.result['total_price']}")
        
        # Step 2: Replace with 2 coke and 1 lemonade (simulating the exact LLM call from logs)
        replace_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "soda",
                    "quantity": 2,
                    "drink_choice": "cola"
                },
                {
                    "item_id": "soda",
                    "quantity": 1,
                    "drink_choice": "lemon_lime"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(replace_params))
        
        # Verify the replacement worked
        self.assertEqual(replace_params.result["status"], "items_updated")
        self.assertEqual(replace_params.result["total_items"], 2)  # Should have 2 different drink types
        
        # Should still cost the same: 2 colas + 1 lemon-lime = 3 * 1.99 = 5.97
        self.assertAlmostEqual(replace_params.result["total_price"], 5.97, places=2)
        
        print(f"Step 2 - Replaced with specific drinks: ${replace_params.result['total_price']}")
        print(f"Items: {replace_params.result['items']}")
        
        # Verify the backend order session has correct data
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 2)
        
        # Check that we have the right drink types
        item_ids = [item["item_id"] for item in current_order_session.current_order_items]
        self.assertIn("cola", item_ids)
        self.assertIn("lemon_lime", item_ids)
        
        # Check quantities
        cola_item = next(item for item in current_order_session.current_order_items if item["item_id"] == "cola")
        lemon_lime_item = next(item for item in current_order_session.current_order_items if item["item_id"] == "lemon_lime")
        
        self.assertEqual(cola_item["quantity"], 2)
        self.assertEqual(lemon_lime_item["quantity"], 1)
        
        print(f"Backend session updated correctly:")
        for item in current_order_session.current_order_items:
            print(f"  - {item['description']}")
    
    def test_single_soda_type_conversion(self):
        """Test converting a single soda with drink_choice."""
        # Step 1: Add a regular soda
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "soda",
                    "quantity": 1,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Step 2: Update to specific cola
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "soda",
                    "drink_choice": "cola"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Should still be 1 item, but now cola
        self.assertEqual(update_params.result["total_items"], 1)
        self.assertAlmostEqual(update_params.result["total_price"], 1.99, places=2)
        
        # Check backend
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        self.assertEqual(current_order_session.current_order_items[0]["item_id"], "cola")

if __name__ == "__main__":
    unittest.main()
