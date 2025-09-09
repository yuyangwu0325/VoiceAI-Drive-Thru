"""
Stress testing and edge cases for the GrillTalk ordering system.
"""

import unittest
import asyncio
import json
from food_ordering import process_food_order
from pipecat.services.llm_service import FunctionCallParams

class MockFunctionCallParams:
    def __init__(self, arguments):
        self.arguments = arguments
        self.result = None
    
    async def result_callback(self, result):
        self.result = result

class TestStressAndEdgeCases(unittest.TestCase):
    """Test cases for stress testing and edge cases."""
    
    def setUp(self):
        """Set up for each test."""
        from food_ordering import current_order_session
        current_order_session.clear_order()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()
    
    def test_large_order(self):
        """Test handling a very large order with many items."""
        # Create a large order with 20+ items
        items = []
        for i in range(5):
            items.extend([
                {"item_id": "burger", "quantity": 3, "size": "large", "combo": False, "customizations": ["extra_cheese"]},
                {"item_id": "fries", "quantity": 2, "size": "medium", "combo": False, "customizations": []},
                {"item_id": "soda", "quantity": 4, "size": "small", "combo": False, "customizations": []},
                {"item_id": "chicken_burger", "quantity": 1, "size": "large", "combo": True, "combo_type": "large_combo", "customizations": ["no_mayo"]},
            ])
        
        params = MockFunctionCallParams({
            "action": "add_item",
            "items": items
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Verify the large order was processed correctly
        self.assertEqual(params.result["status"], "items_added")
        self.assertEqual(params.result["total_items"], 20)  # 5 sets of 4 items each
        self.assertGreater(params.result["total_price"], 100)  # Should be a substantial total
    
    def test_maximum_quantity_single_item(self):
        """Test ordering a very large quantity of a single item."""
        params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 99,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Verify large quantity is handled
        self.assertEqual(params.result["status"], "items_added")
        self.assertEqual(params.result["total_items"], 1)
        expected_price = 99 * 7.49  # 99 medium burgers
        self.assertAlmostEqual(params.result["total_price"], expected_price, places=2)
    
    def test_all_customizations_single_item(self):
        """Test adding all possible customizations to a single item."""
        params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": ["extra_cheese", "extra_sauce", "gluten_free_bun", "no_mayo", "no_lettuce", "no_tomato", "no_onion"]
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Verify all customizations are applied
        self.assertEqual(params.result["status"], "items_added")
        # Base: 5.99 + Large: 2.50 + Extra cheese: 0.75 + Extra sauce: 0.50 + Gluten-free: 1.50 = 11.24
        self.assertAlmostEqual(params.result["total_price"], 11.24, places=2)
        self.assertIn("Extra cheese", params.result["items"][0])
        self.assertIn("Gluten-free bun", params.result["items"][0])
    
    def test_rapid_order_modifications(self):
        """Test rapid successive modifications to an order."""
        # Start with a basic order
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {"item_id": "burger", "quantity": 1, "size": "small", "combo": False, "customizations": []}
            ]
        })
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Perform multiple rapid modifications
        modifications = [
            {"action": "update_items", "items": [{"item_id": "burger", "size": "medium"}]},
            {"action": "update_items", "items": [{"item_id": "burger", "quantity": 2}]},
            {"action": "update_items", "items": [{"item_id": "burger", "combo": True, "combo_type": "regular_combo"}]},
            {"action": "update_items", "items": [{"item_id": "burger", "customizations": ["extra_cheese", "no_mayo"]}]},
            {"action": "update_items", "items": [{"item_id": "burger", "size": "large"}]},
        ]
        
        for mod in modifications:
            params = MockFunctionCallParams(mod)
            self.loop.run_until_complete(process_food_order(params))
            self.assertEqual(params.result["status"], "items_updated")
        
        # Final state should be: 2x Large Burger Regular Combo with customizations
        self.assertGreater(params.result["total_price"], 20)  # Should be substantial
    
    def test_empty_order_operations(self):
        """Test operations on empty orders."""
        # Try to update items when no order exists
        params = MockFunctionCallParams({
            "action": "update_items",
            "items": [{"item_id": "burger", "quantity": 1}]
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Should handle gracefully
        self.assertEqual(params.result["status"], "error")
        self.assertIn("No active order", params.result["message"])
    
    def test_finalize_empty_order(self):
        """Test finalizing an empty order."""
        params = MockFunctionCallParams({
            "action": "finalize"
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Should handle gracefully
        self.assertEqual(params.result["status"], "error")
        self.assertIn("No active order", params.result["message"])
    
    def test_mixed_valid_invalid_items(self):
        """Test adding a mix of valid and invalid items."""
        params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {"item_id": "burger", "quantity": 1, "size": "medium", "combo": False, "customizations": []},
                {"item_id": "invalid_item", "quantity": 1, "size": "medium", "combo": False, "customizations": []},
                {"item_id": "fries", "quantity": 1, "size": "large", "combo": False, "customizations": []},
                {"item_id": "another_invalid", "quantity": 2, "size": "small", "combo": False, "customizations": []}
            ]
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Should process valid items and ignore invalid ones
        self.assertEqual(params.result["status"], "items_added")
        self.assertEqual(params.result["total_items"], 2)  # Only burger and fries
        # Burger (7.49) + Large fries (5.49) = 12.98
        self.assertAlmostEqual(params.result["total_price"], 12.98, places=2)
    
    def test_extreme_price_calculation(self):
        """Test price calculation with extreme values."""
        params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burrito",
                    "quantity": 50,
                    "size": "large",
                    "combo": True,
                    "combo_type": "large_combo",
                    "customizations": ["extra_cheese", "extra_sauce", "gluten_free_bun"],
                    "protein": "steak"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Verify extreme calculation is handled correctly
        self.assertEqual(params.result["status"], "items_added")
        self.assertGreater(params.result["total_price"], 500)  # Should be very high
        self.assertIsInstance(params.result["total_price"], (int, float))  # Should be numeric

if __name__ == "__main__":
    unittest.main()
