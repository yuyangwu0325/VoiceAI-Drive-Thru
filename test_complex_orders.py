"""
Test script for complex order scenarios including:
- Adding multiple items
- Updating quantities
- Removing items from multi-line orders
- Verifying price calculations throughout
"""

import unittest
import asyncio
import json
from food_ordering import process_food_order
from pipecat.services.llm_service import FunctionCallParams
from order_session import OrderSession

# Create a mock FunctionCallParams class for testing
class MockFunctionCallParams:
    def __init__(self, arguments):
        self.arguments = arguments
        self.result = None
    
    async def result_callback(self, result):
        self.result = result

class TestComplexOrders(unittest.TestCase):
    """Test cases for complex order scenarios."""
    
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
    
    def test_add_multiple_items(self):
        """Test adding multiple items to an order."""
        # Add multiple items in a single call
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 2,
                    "size": "medium",
                    "combo": False,
                    "customizations": ["extra_cheese"]
                },
                {
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": []
                },
                {
                    "item_id": "soda",
                    "quantity": 3,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Check the result
        self.assertEqual(add_params.result["status"], "items_added")
        self.assertEqual(add_params.result["total_items"], 3)  # 3 different items
        
        # Calculate expected price:
        # 2 medium burgers with extra cheese: 2 * (5.99 + 1.50 + 0.75) = 2 * 8.24 = 16.48
        # 1 large fries: 2.99 + 2.50 = 5.49
        # 3 medium sodas: 3 * (1.99 + 1.50) = 3 * 3.49 = 10.47
        # Total: 16.48 + 5.49 + 10.47 = 32.44
        self.assertAlmostEqual(add_params.result["total_price"], 32.44, places=2)
    
    def test_update_quantity_by_adding_same_item(self):
        """Test updating quantity by adding the same item again."""
        # First add a burger
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
        
        # Now add another burger with the same specifications
        add_params2 = MockFunctionCallParams({
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
        
        # Manually set the last_item_timestamp to simulate a quick duplicate request
        from food_ordering import current_order_session
        current_order_session.last_item_timestamp = current_order_session.last_item_timestamp - 1.0
        
        self.loop.run_until_complete(process_food_order(add_params2))
        
        # Check the result - should have increased quantity instead of adding new item
        self.assertEqual(add_params2.result["status"], "items_added")
        self.assertEqual(add_params2.result["total_items"], 1)  # Still just 1 line item
        
        # Check that the price is correct (2 medium burgers)
        # 2 * (5.99 + 1.50) = 2 * 7.49 = 14.98
        self.assertAlmostEqual(add_params2.result["total_price"], 14.98, places=2)
        
        # Verify the quantity is now 2
        from food_ordering import current_order_session
        self.assertEqual(current_order_session.current_order_items[0]["quantity"], 2)
    
    def test_update_quantity_explicitly(self):
        """Test explicitly updating the quantity of an item."""
        # First add a burger
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
        
        # Now update the quantity to 3
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 3
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Check the result
        self.assertEqual(update_params.result["status"], "items_updated")
        self.assertEqual(update_params.result["total_items"], 1)
        
        # Check that the price is correct (3 medium burgers)
        # 3 * (5.99 + 1.50) = 3 * 7.49 = 22.47
        self.assertAlmostEqual(update_params.result["total_price"], 22.47, places=2)
        
        # Verify the quantity is now 3
        from food_ordering import current_order_session
        self.assertEqual(current_order_session.current_order_items[0]["quantity"], 3)
    
    def test_remove_item_from_multi_line_order(self):
        """Test removing an item from a multi-line order."""
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
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": []
                },
                {
                    "item_id": "soda",
                    "quantity": 2,
                    "size": "small",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Verify we have 3 items
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 3)
        
        # Now remove the fries
        remove_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "fries",
                    "action": "remove"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(remove_params))
        
        # Check the result
        self.assertEqual(remove_params.result["status"], "items_updated")
        self.assertEqual(remove_params.result["total_items"], 2)  # Should have 2 items left
        
        # Calculate expected price:
        # 1 medium burger: 5.99 + 1.50 = 7.49
        # 2 small sodas: 2 * 1.99 = 3.98
        # Total: 7.49 + 3.98 = 11.47
        self.assertAlmostEqual(remove_params.result["total_price"], 11.47, places=2)
        
        # Verify the fries were removed
        items = current_order_session.current_order_items
        item_ids = [item["item_id"] for item in items]
        self.assertNotIn("fries", item_ids)
        self.assertIn("burger", item_ids)
        self.assertIn("soda", item_ids)
    
    def test_complex_order_workflow(self):
        """Test a complex order workflow with multiple operations."""
        # Step 1: Add a burger and fries
        add_params1 = MockFunctionCallParams({
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
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params1))
        
        # Check initial state
        self.assertEqual(add_params1.result["total_items"], 2)
        # 1 medium burger: 5.99 + 1.50 = 7.49
        # 1 medium fries: 2.99 + 1.50 = 4.49
        # Total: 7.49 + 4.49 = 11.98
        self.assertAlmostEqual(add_params1.result["total_price"], 11.98, places=2)
        
        # Step 2: Update burger to be a combo
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "combo": True,
                    "combo_type": "regular_combo"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Check after combo update
        self.assertEqual(update_params.result["total_items"], 2)
        # Combo pricing: 5.99 (burger) + 1.50 (medium) + 2.99 (fries) + 1.99 (soda) - 1.50 (discount) = 10.97
        # Medium fries: 2.99 + 1.50 = 4.49
        # Total: 10.97 + 4.49 = 15.46
        self.assertAlmostEqual(update_params.result["total_price"], 15.46, places=2)
        
        # Step 3: Add a soda
        add_params2 = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "soda",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params2))
        
        # Check after adding soda
        self.assertEqual(add_params2.result["total_items"], 3)
        # Combo pricing: 10.97
        # Medium fries: 4.49
        # Large soda: 1.99 + 2.50 = 4.49
        # Total: 10.97 + 4.49 + 4.49 = 19.95
        self.assertAlmostEqual(add_params2.result["total_price"], 19.95, places=2)
        
        # Step 4: Update fries quantity to 2
        update_params2 = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "fries",
                    "quantity": 2
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params2))
        
        # Check after updating fries quantity
        self.assertEqual(update_params2.result["total_items"], 3)
        # Combo pricing: 10.97
        # 2 Medium fries: 2 * 4.49 = 8.98
        # Large soda: 4.49
        # Total: 10.97 + 8.98 + 4.49 = 24.44
        self.assertAlmostEqual(update_params2.result["total_price"], 24.44, places=2)
        
        # Step 5: Remove the soda
        remove_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "soda",
                    "action": "remove"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(remove_params))
        
        # Check after removing soda
        self.assertEqual(remove_params.result["total_items"], 2)
        # Combo pricing: 10.97
        # 2 Medium fries: 8.98
        # Total: 10.97 + 8.98 = 19.95
        self.assertAlmostEqual(remove_params.result["total_price"], 19.95, places=2)
        
        # Step 6: Finalize the order
        finalize_params = MockFunctionCallParams({
            "action": "finalize"
        })
        
        self.loop.run_until_complete(process_food_order(finalize_params))
        
        # Check final order
        self.assertEqual(finalize_params.result["status"], "order_finalized")
        self.assertEqual(finalize_params.result["total_items"], 2)
        self.assertAlmostEqual(finalize_params.result["total_price"], 19.95, places=2)
    
    def test_reduce_quantity(self):
        """Test reducing the quantity of an item."""
        # Add a burger with quantity 3
        add_params = MockFunctionCallParams({
            "action": "add_item",
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
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Check initial state
        self.assertEqual(add_params.result["total_items"], 1)
        # 3 medium burgers: 3 * (5.99 + 1.50) = 3 * 7.49 = 22.47
        self.assertAlmostEqual(add_params.result["total_price"], 22.47, places=2)
        
        # Now reduce the quantity to 1
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Check after reducing quantity
        self.assertEqual(update_params.result["total_items"], 1)
        # 1 medium burger: 5.99 + 1.50 = 7.49
        self.assertAlmostEqual(update_params.result["total_price"], 7.49, places=2)
        
        # Verify the quantity is now 1
        from food_ordering import current_order_session
        self.assertEqual(current_order_session.current_order_items[0]["quantity"], 1)
    
    def test_remove_by_setting_quantity_to_zero(self):
        """Test removing an item by setting its quantity to zero."""
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
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Now set the burger quantity to 0
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 0
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Check the result
        self.assertEqual(update_params.result["status"], "items_updated")
        self.assertEqual(update_params.result["total_items"], 1)  # Should have 1 item left
        
        # Calculate expected price:
        # 1 large fries: 2.99 + 2.50 = 5.49
        self.assertAlmostEqual(update_params.result["total_price"], 5.49, places=2)
        
        # Verify the burger was removed
        from food_ordering import current_order_session
        items = current_order_session.current_order_items
        item_ids = [item["item_id"] for item in items]
        self.assertNotIn("burger", item_ids)
        self.assertIn("fries", item_ids)

if __name__ == "__main__":
    unittest.main()
