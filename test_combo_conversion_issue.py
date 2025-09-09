"""
Test script specifically for the combo conversion issue where LLM adds new line instead of updating existing item.
This addresses the issue where asking to "make it a combo" results in a duplicate line item.
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

class TestComboConversionIssue(unittest.TestCase):
    """Test cases specifically for combo conversion issues."""
    
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
    
    def test_chicken_burrito_combo_conversion_correct_way(self):
        """Test the CORRECT way to convert a chicken burrito to combo using update_items."""
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
        initial_price = add_params.result["total_price"]
        self.assertAlmostEqual(initial_price, 8.49, places=2)  # Regular chicken burrito
        
        print(f"Step 1 - Added chicken burrito: ${initial_price}")
        
        # Step 2: CORRECTLY convert to combo using update_items
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "chicken_burrito",
                    "combo": True,
                    "combo_type": "regular_combo"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Verify the conversion worked correctly
        self.assertEqual(update_params.result["status"], "items_updated")
        self.assertEqual(update_params.result["total_items"], 1)  # Should still be 1 item, not 2!
        
        # Calculate expected combo price:
        # Chicken burrito: 8.49 + Fries: 2.99 + Soda: 1.99 - Discount: 1.50 = 11.97
        expected_combo_price = 11.97
        self.assertAlmostEqual(update_params.result["total_price"], expected_combo_price, places=2)
        
        print(f"Step 2 - Converted to combo: ${update_params.result['total_price']}")
        print(f"Items: {update_params.result['items']}")
        
        # Verify the description shows it's a combo
        self.assertIn("Regular Combo", update_params.result["items"][0])
    
    def test_chicken_burrito_combo_conversion_wrong_way(self):
        """Test the WRONG way that LLM might do - adding new combo item instead of updating."""
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
        
        # Step 2: INCORRECTLY add a new combo item (what LLM might do wrong)
        wrong_add_params = MockFunctionCallParams({
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
        
        self.loop.run_until_complete(process_food_order(wrong_add_params))
        
        # This will result in 2 items instead of 1 updated item
        self.assertEqual(wrong_add_params.result["status"], "items_added")
        self.assertEqual(wrong_add_params.result["total_items"], 2)  # WRONG! Should be 1
        
        # Total will be: Regular chicken burrito (8.49) + Combo chicken burrito (11.97) = 20.46
        expected_wrong_total = 8.49 + 11.97  # 20.46
        self.assertAlmostEqual(wrong_add_params.result["total_price"], expected_wrong_total, places=2)
        
        print(f"WRONG WAY - Total items: {wrong_add_params.result['total_items']}")
        print(f"WRONG WAY - Total price: ${wrong_add_params.result['total_price']}")
        print(f"WRONG WAY - Items: {wrong_add_params.result['items']}")
        
        # This demonstrates the problem - customer gets charged for both items!
    
    def test_burger_combo_conversion_scenarios(self):
        """Test combo conversion scenarios with burgers."""
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
        
        # Verify initial state: Medium burger with extra cheese = 5.99 + 1.50 + 0.75 = 8.24
        self.assertEqual(add_params.result["total_items"], 1)
        self.assertAlmostEqual(add_params.result["total_price"], 8.24, places=2)
        
        # Step 2: Convert to combo correctly
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
        
        # Should still be 1 item, now as combo
        self.assertEqual(update_params.result["total_items"], 1)
        
        # Expected: Medium burger (7.49) + extra cheese (0.75) + fries (2.99) + soda (1.99) - discount (1.50) = 11.72
        expected_price = 11.72
        self.assertAlmostEqual(update_params.result["total_price"], expected_price, places=2)
        
        # Verify it's described as a combo
        self.assertIn("Regular Combo", update_params.result["items"][0])
        self.assertIn("Extra cheese", update_params.result["items"][0])
    
    def test_multiple_items_selective_combo_conversion(self):
        """Test converting only one item to combo when multiple items exist."""
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
                    "item_id": "chicken_burrito",
                    "quantity": 1,
                    "size": "regular",
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
        
        # Verify initial state: 3 items
        self.assertEqual(add_params.result["total_items"], 3)
        initial_total = add_params.result["total_price"]
        
        # Step 2: Convert only the burger to combo
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
        
        # Should still have 3 items (burger combo + chicken burrito + fries)
        self.assertEqual(update_params.result["total_items"], 3)
        
        # The burger should now be a combo, others unchanged
        items = update_params.result["items"]
        combo_item = next((item for item in items if "Regular Combo" in item), None)
        self.assertIsNotNone(combo_item, "Should have one combo item")
        
        # Should have exactly one combo item
        combo_count = sum(1 for item in items if "Combo" in item)
        self.assertEqual(combo_count, 1, "Should have exactly one combo item")
    
    def test_duplicate_detection_vs_combo_conversion(self):
        """Test that duplicate detection doesn't interfere with combo conversion."""
        # Step 1: Add a chicken burrito
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
        
        # Step 2: Convert to combo (should use update_items, not add_item)
        update_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "chicken_burrito",
                    "combo": True,
                    "combo_type": "regular_combo"
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(update_params))
        
        # Should be 1 item (converted to combo), not 2 items
        self.assertEqual(update_params.result["total_items"], 1)
        self.assertEqual(update_params.result["status"], "items_updated")
        
        # Step 3: Try to add the same combo again (this should trigger duplicate detection)
        duplicate_params = MockFunctionCallParams({
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
        
        # Simulate quick duplicate by adjusting timestamp
        from food_ordering import current_order_session
        current_order_session.last_item_timestamp = current_order_session.last_item_timestamp - 1.0
        
        self.loop.run_until_complete(process_food_order(duplicate_params))
        
        # Should still be 1 item with increased quantity, not 2 separate items
        self.assertEqual(duplicate_params.result["total_items"], 1)
        
        # Check if duplicate handling was triggered
        if "duplicate_handling" in duplicate_params.result:
            print("Duplicate detection worked correctly")
        
        # Verify the quantity increased
        from food_ordering import current_order_session
        self.assertEqual(current_order_session.current_order_items[0]["quantity"], 2)

if __name__ == "__main__":
    unittest.main()
