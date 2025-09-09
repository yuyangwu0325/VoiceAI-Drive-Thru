"""
Test script to verify the fixes for quantity consolidation and removal issues.
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

class TestQuantityConsolidationFix(unittest.TestCase):
    """Test cases for quantity consolidation and removal fixes."""
    
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
    
    def test_add_more_burrito_consolidation(self):
        """Test that 'add more burrito' consolidates quantity instead of creating new line."""
        # Step 1: Add a beef burrito combo
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burrito",
                    "quantity": 1,
                    "size": "regular",
                    "combo": True,
                    "combo_type": "regular_combo",
                    "protein": "beef",
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Verify initial state
        self.assertEqual(add_params.result["status"], "items_added")
        self.assertEqual(add_params.result["total_items"], 1)
        initial_price = add_params.result["total_price"]
        
        print(f"Step 1 - Added 1 beef burrito combo: ${initial_price}")
        
        # Step 2: "Add more burrito" - should consolidate, not create new line
        add_more_params = MockFunctionCallParams({
            "items": [  # No action - defaults to add_item, but should be smart converted
                {
                    "item_id": "burrito",
                    "quantity": 1,
                    "combo": True,
                    "combo_type": "regular_combo",
                    "protein": "beef",
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_more_params))
        
        # Verify consolidation worked
        self.assertEqual(add_more_params.result["status"], "items_updated")
        self.assertEqual(add_more_params.result["total_items"], 1)  # Should still be 1 item!
        self.assertTrue(add_more_params.result.get("smart_conversion", False))
        
        # Should be 2x the original price
        expected_price = initial_price * 2
        self.assertAlmostEqual(add_more_params.result["total_price"], expected_price, places=2)
        
        print(f"Step 2 - Consolidated to 2 burritos: ${add_more_params.result['total_price']}")
        
        # Verify the backend has correct quantity
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        self.assertEqual(current_order_session.current_order_items[0]["quantity"], 2)
    
    def test_add_more_fries_consolidation(self):
        """Test that 'add more fries' consolidates quantity instead of creating new line."""
        # Step 1: Add 5 fries
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "fries",
                    "quantity": 5,
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
        initial_price = add_params.result["total_price"]
        
        print(f"Step 1 - Added 5 fries: ${initial_price}")
        
        # Step 2: "Add 4 more fries" - should consolidate to 9 total
        add_more_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "fries",
                    "quantity": 4,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_more_params))
        
        # Verify consolidation worked
        self.assertEqual(add_more_params.result["status"], "items_updated")
        self.assertEqual(add_more_params.result["total_items"], 1)  # Should still be 1 item!
        self.assertTrue(add_more_params.result.get("smart_conversion", False))
        
        # Should be 9 fries total (5 + 4)
        expected_price = 9 * 2.99  # 9 regular fries at $2.99 each
        self.assertAlmostEqual(add_more_params.result["total_price"], expected_price, places=2)
        
        print(f"Step 2 - Consolidated to 9 fries: ${add_more_params.result['total_price']}")
        
        # Verify the backend has correct quantity
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        self.assertEqual(current_order_session.current_order_items[0]["quantity"], 9)
    
    def test_remove_item_by_quantity_zero(self):
        """Test that setting quantity to 0 properly removes the item."""
        # Step 1: Add multiple items
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
                    "quantity": 3,
                    "size": "large",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Verify initial state
        self.assertEqual(add_params.result["total_items"], 2)
        initial_price = add_params.result["total_price"]
        
        print(f"Step 1 - Added burger and fries: ${initial_price}")
        
        # Step 2: Remove fries by setting quantity to 0
        remove_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "fries",
                    "quantity": 0
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(remove_params))
        
        # Verify removal worked
        self.assertEqual(remove_params.result["status"], "items_updated")
        self.assertEqual(remove_params.result["total_items"], 1)  # Should have 1 item left
        self.assertEqual(len(remove_params.result["removed_items"]), 1)  # Should show 1 removed
        
        # Should only have burger price left
        burger_price = 7.49  # Medium burger: 5.99 + 1.50
        self.assertAlmostEqual(remove_params.result["total_price"], burger_price, places=2)
        
        print(f"Step 2 - Removed fries, left with burger: ${remove_params.result['total_price']}")
        
        # Verify the backend has correct items
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        self.assertEqual(current_order_session.current_order_items[0]["item_id"], "burger")
    
    def test_smart_conversion_remove_by_quantity_zero(self):
        """Test that smart conversion properly handles quantity 0 removal."""
        # Step 1: Add fries
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "fries",
                    "quantity": 4,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Step 2: LLM tries to "remove fries" by setting quantity to 0 with add_item
        remove_params = MockFunctionCallParams({
            "items": [  # No action - should be smart converted to update
                {
                    "item_id": "fries",
                    "quantity": 0
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(remove_params))
        
        # Verify smart conversion removal worked
        self.assertEqual(remove_params.result["status"], "items_updated")
        self.assertEqual(remove_params.result["total_items"], 0)  # Should have no items left
        self.assertTrue(remove_params.result.get("smart_conversion", False))
        self.assertEqual(len(remove_params.result["removed_items"]), 1)  # Should show 1 removed
        self.assertEqual(remove_params.result["total_price"], 0)
        
        print(f"Step 2 - Smart conversion removed all fries: ${remove_params.result['total_price']}")
        
        # Verify the backend has no items
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 0)

if __name__ == "__main__":
    unittest.main()
