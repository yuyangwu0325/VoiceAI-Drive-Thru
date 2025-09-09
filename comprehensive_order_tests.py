"""
Comprehensive test suite for GrillTalk ordering system.
Tests all major functionality including:
- Adding multiple orders
- Checking amounts and totals
- Adding/removing quantities
- Modifying orders
- Complex order workflows
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

class ComprehensiveOrderTests(unittest.TestCase):
    """Comprehensive test cases for the GrillTalk ordering system."""
    
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
    
    def test_single_item_order(self):
        """Test ordering a single item."""
        params = MockFunctionCallParams({
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
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Verify results
        self.assertEqual(params.result["status"], "items_added")
        self.assertEqual(params.result["total_items"], 1)
        self.assertAlmostEqual(params.result["total_price"], 7.49, places=2)  # 5.99 + 1.50
        self.assertIn("1x Medium Burger", params.result["items"][0])
    
    def test_multiple_items_single_call(self):
        """Test adding multiple different items in a single call."""
        params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 2,
                    "size": "large",
                    "combo": False,
                    "customizations": ["extra_cheese"]
                },
                {
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                },
                {
                    "item_id": "soda",
                    "quantity": 3,
                    "size": "small",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Verify results
        self.assertEqual(params.result["status"], "items_added")
        self.assertEqual(params.result["total_items"], 3)
        
        # Calculate expected total:
        # 2 large burgers with extra cheese: 2 * (5.99 + 2.50 + 0.75) = 18.48
        # 1 medium fries: 2.99 + 1.50 = 4.49
        # 3 small sodas: 3 * 1.99 = 5.97
        # Total: 18.48 + 4.49 + 5.97 = 28.94
        self.assertAlmostEqual(params.result["total_price"], 28.94, places=2)
    
    def test_combo_order(self):
        """Test ordering combo meals."""
        params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1,
                    "size": "large",
                    "combo": True,
                    "combo_type": "large_combo",
                    "customizations": [],
                    "drink_choice": "cola"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Verify results
        self.assertEqual(params.result["status"], "items_added")
        self.assertEqual(params.result["total_items"], 1)
        
        # Calculate expected total:
        # Large burger: 5.99 + 2.50 = 8.49
        # Large fries: 2.99 + 2.50 = 5.49
        # Large soda: 1.99 + 2.50 = 4.49
        # Subtotal: 18.47, Discount: 2.00, Total: 16.47
        self.assertAlmostEqual(params.result["total_price"], 16.47, places=2)
    
    def test_quantity_updates(self):
        """Test updating item quantities."""
        # First add an item
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
        
        # Verify results
        self.assertEqual(update_params.result["status"], "items_updated")
        self.assertEqual(update_params.result["total_items"], 1)
        self.assertAlmostEqual(update_params.result["total_price"], 22.47, places=2)  # 3 * 7.49
    
    def test_size_modifications(self):
        """Test changing item sizes."""
        # First add a small burger
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1,
                    "size": "small",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Now upgrade to large
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "size": "large"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Verify results
        self.assertEqual(update_params.result["status"], "items_updated")
        self.assertAlmostEqual(update_params.result["total_price"], 8.49, places=2)  # 5.99 + 2.50
    
    def test_combo_conversion(self):
        """Test converting regular items to combos."""
        # First add a regular burger and fries
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
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Verify initial total
        self.assertAlmostEqual(add_params.result["total_price"], 11.98, places=2)  # 7.49 + 4.49
        
        # Now convert burger to combo
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "combo": True,
                    "combo_type": "regular_combo",
                    "drink_choice": "cola"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Verify results - should have combo + separate fries
        self.assertEqual(update_params.result["status"], "items_updated")
        self.assertEqual(update_params.result["total_items"], 2)
        
        # Expected: Medium burger combo (10.97) + Medium fries (4.49) = 15.46
        self.assertAlmostEqual(update_params.result["total_price"], 15.46, places=2)
    
    def test_customization_changes(self):
        """Test adding and removing customizations."""
        # First add a plain burger
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
        
        # Now add customizations
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "customizations": ["extra_cheese", "extra_sauce", "no_mayo"]
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Verify results
        self.assertEqual(update_params.result["status"], "items_updated")
        # Expected: 7.49 + 0.75 + 0.50 = 8.74
        self.assertAlmostEqual(update_params.result["total_price"], 8.74, places=2)
    
    def test_protein_upgrades(self):
        """Test protein upgrades."""
        # Add a burrito with steak
        params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burrito",
                    "quantity": 1,
                    "size": "large",
                    "combo": False,
                    "customizations": [],
                    "protein": "steak"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(params))
        
        # Verify results
        self.assertEqual(params.result["status"], "items_added")
        # Expected: 7.99 + 2.50 + 1.50 = 11.99
        self.assertAlmostEqual(params.result["total_price"], 11.99, places=2)
    
    def test_duplicate_detection(self):
        """Test duplicate order detection."""
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
        
        # Add the same burger again quickly (simulate duplicate)
        from food_ordering import current_order_session
        current_order_session.last_item_timestamp = current_order_session.last_item_timestamp - 1.0
        
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
        
        self.loop.run_until_complete(process_food_order(add_params2))
        
        # Verify duplicate was handled
        self.assertEqual(add_params2.result["status"], "items_added")
        self.assertEqual(add_params2.result["total_items"], 1)  # Still one line item
        self.assertAlmostEqual(add_params2.result["total_price"], 14.98, places=2)  # 2 * 7.49
        self.assertIn("duplicate_handling", add_params2.result)
    
    def test_order_finalization(self):
        """Test order finalization process."""
        # Add items to order
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 2,
                    "size": "medium",
                    "combo": True,
                    "combo_type": "regular_combo",
                    "customizations": ["extra_cheese"]
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
        
        # Finalize the order
        finalize_params = MockFunctionCallParams({
            "action": "finalize"
        })
        
        self.loop.run_until_complete(process_food_order(finalize_params))
        
        # Verify finalization
        self.assertEqual(finalize_params.result["status"], "order_finalized")
        self.assertIn("invoice_id", finalize_params.result)
        self.assertIn("total_price", finalize_params.result)
        self.assertEqual(finalize_params.result["payment_status"], "processing")
        
        # Verify order session is cleared
        from food_ordering import current_order_session
        self.assertFalse(current_order_session.is_order_active)
    
    def test_order_clearing(self):
        """Test clearing an order."""
        # Add items to order
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
        
        # Clear the order
        clear_params = MockFunctionCallParams({
            "action": "clear"
        })
        
        self.loop.run_until_complete(process_food_order(clear_params))
        
        # Verify clearing
        self.assertEqual(clear_params.result["status"], "order_cleared")
        
        # Verify order session is cleared
        from food_ordering import current_order_session
        self.assertFalse(current_order_session.is_order_active)
        self.assertEqual(len(current_order_session.current_order_items), 0)
    
    def test_complex_workflow(self):
        """Test a complex order workflow with multiple operations."""
        # Step 1: Add initial items
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1,
                    "size": "small",
                    "combo": False,
                    "customizations": []
                },
                {
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "small",
                    "combo": False,
                    "customizations": []
                },
                {
                    "item_id": "soda",
                    "quantity": 1,
                    "size": "small",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        initial_total = add_params.result["total_price"]
        
        # Step 2: Upgrade burger to combo
        combo_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "combo": True,
                    "combo_type": "regular_combo"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(combo_params))
        
        # Step 3: Increase fries quantity
        quantity_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "fries",
                    "quantity": 2
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(quantity_params))
        
        # Step 4: Add customizations to burger
        custom_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "customizations": ["extra_cheese", "no_mayo"]
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(custom_params))
        
        # Step 5: Upgrade soda size
        size_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "soda",
                    "size": "large"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(size_params))
        
        # Verify final state
        self.assertEqual(size_params.result["status"], "items_updated")
        self.assertEqual(size_params.result["total_items"], 3)
        
        # Final total should be higher than initial
        self.assertGreater(size_params.result["total_price"], initial_total)
        
        # Step 6: Finalize order
        finalize_params = MockFunctionCallParams({
            "action": "finalize"
        })
        
        self.loop.run_until_complete(process_food_order(finalize_params))
        
        # Verify finalization
        self.assertEqual(finalize_params.result["status"], "order_finalized")
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test invalid item ID
        invalid_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "invalid_item",
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(invalid_params))
        
        # Should handle gracefully
        self.assertEqual(invalid_params.result["status"], "items_added")
        self.assertEqual(invalid_params.result["total_items"], 0)
        self.assertEqual(invalid_params.result["total_price"], 0)
    
    def test_pricing_accuracy(self):
        """Test pricing accuracy across different scenarios."""
        test_cases = [
            # (items, expected_total)
            ([{"item_id": "burger", "quantity": 1, "size": "small"}], 5.99),
            ([{"item_id": "burger", "quantity": 1, "size": "medium"}], 7.49),
            ([{"item_id": "burger", "quantity": 1, "size": "large"}], 8.49),
            ([{"item_id": "burger", "quantity": 2, "size": "medium"}], 14.98),
            ([{"item_id": "fries", "quantity": 1, "size": "large"}], 5.49),
            ([{"item_id": "soda", "quantity": 3, "size": "small"}], 5.97),
        ]
        
        for items, expected_total in test_cases:
            with self.subTest(items=items):
                # Clear order first
                from food_ordering import current_order_session
                current_order_session.clear_order()
                
                params = MockFunctionCallParams({
                    "action": "add_item",
                    "items": [dict(item, combo=False, customizations=[]) for item in items]
                })
                
                self.loop.run_until_complete(process_food_order(params))
                
                self.assertAlmostEqual(
                    params.result["total_price"], 
                    expected_total, 
                    places=2,
                    msg=f"Failed for items: {items}"
                )

if __name__ == "__main__":
    unittest.main()
