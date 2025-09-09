"""
Test script for food ordering functionality.
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

class TestFoodOrdering(unittest.TestCase):
    """Test cases for food ordering functionality."""
    
    def setUp(self):
        """Set up for each test."""
        # Reset the current order session
        from food_ordering import current_order_session
        current_order_session.clear_order()
    
    def test_add_item(self):
        """Test adding an item to the order."""
        # Create a mock function call params
        params = MockFunctionCallParams({
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
        
        # Process the order
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_food_order(params))
        
        # Check the result
        self.assertEqual(params.result["status"], "items_added")
        self.assertEqual(len(params.result["items"]), 1)
        self.assertEqual(params.result["total_items"], 1)
        
        # Check that the price is correct (medium burger with extra cheese)
        # 5.99 (base) + 1.50 (medium) + 0.75 (extra cheese) = 8.24
        self.assertAlmostEqual(params.result["total_price"], 8.24, places=2)
    
    def test_add_combo(self):
        """Test adding a combo to the order."""
        # Create a mock function call params
        params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1,
                    "size": "medium",
                    "combo": True,
                    "combo_type": "regular_combo",
                    "customizations": []
                }
            ]
        })
        
        # Process the order
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_food_order(params))
        
        # Check the result
        self.assertEqual(params.result["status"], "items_added")
        self.assertEqual(len(params.result["items"]), 1)
        self.assertEqual(params.result["total_items"], 1)
        
        # Check that the price is correct (medium burger combo)
        # 5.99 (base) + 1.50 (medium) + 2.99 (fries) + 1.99 (soda) - 1.50 (discount) = 10.97
        self.assertAlmostEqual(params.result["total_price"], 10.97, places=2)
    
    def test_update_item(self):
        """Test updating an item in the order."""
        # First add an item
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
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_food_order(add_params))
        
        # Now update the item to make it a combo
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
        
        loop.run_until_complete(process_food_order(update_params))
        
        # Check the result
        self.assertEqual(update_params.result["status"], "items_updated")
        self.assertEqual(update_params.result["total_items"], 1)
        
        # Check that the price is correct (small burger combo)
        # 5.99 (base) + 0.00 (small) + 2.99 (fries) + 1.99 (soda) - 1.50 (discount) = 9.47
        self.assertAlmostEqual(update_params.result["total_price"], 9.47, places=2)
    
    def test_remove_item(self):
        """Test removing an item from the order."""
        # First add two items
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
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_food_order(add_params))
        
        # Now remove the burger
        remove_params = MockFunctionCallParams({
            "action": "update_items",
            "items": [
                {
                    "item_id": "burger",
                    "action": "remove"
                }
            ]
        })
        
        loop.run_until_complete(process_food_order(remove_params))
        
        # Check the result
        self.assertEqual(remove_params.result["status"], "items_updated")
        self.assertEqual(remove_params.result["total_items"], 1)
        
        # Check that the price is correct (medium fries only)
        # 2.99 (base) + 1.50 (medium) = 4.49
        self.assertAlmostEqual(remove_params.result["total_price"], 4.49, places=2)
    
    def test_finalize_order(self):
        """Test finalizing an order."""
        # First add an item
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
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_food_order(add_params))
        
        # Now finalize the order
        finalize_params = MockFunctionCallParams({
            "action": "finalize"
        })
        
        loop.run_until_complete(process_food_order(finalize_params))
        
        # Check the result
        self.assertEqual(finalize_params.result["status"], "order_finalized")
        self.assertEqual(finalize_params.result["total_items"], 1)
        
        # Check that the price is correct (small burger)
        # 5.99 (base) + 0.00 (small) = 5.99
        self.assertAlmostEqual(finalize_params.result["total_price"], 5.99, places=2)
        
        # Check that the order is no longer active
        from food_ordering import current_order_session
        self.assertFalse(current_order_session.is_order_active)
    
    def test_clear_order(self):
        """Test clearing an order."""
        # First add an item
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
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_food_order(add_params))
        
        # Now clear the order
        clear_params = MockFunctionCallParams({
            "action": "clear"
        })
        
        loop.run_until_complete(process_food_order(clear_params))
        
        # Check the result
        self.assertEqual(clear_params.result["status"], "order_cleared")
        
        # Check that the order is no longer active
        from food_ordering import current_order_session
        self.assertFalse(current_order_session.is_order_active)
        self.assertEqual(len(current_order_session.current_order_items), 0)
    


    def test_remove_fries(self):
        """Test removing fries from the order."""
        # First add fries
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_food_order(add_params))
        
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
        
        loop.run_until_complete(process_food_order(remove_params))
        
        # Check the result
        self.assertEqual(remove_params.result["status"], "items_updated")
        self.assertEqual(remove_params.result["total_items"], 0)
        self.assertEqual(remove_params.result["total_price"], 0)

    def test_remove_fries(self):
        """Test removing fries from the order."""
        # First add fries
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_food_order(add_params))
        
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
        
        loop.run_until_complete(process_food_order(remove_params))
        
        # Check the result
        self.assertEqual(remove_params.result["status"], "items_updated")
        self.assertEqual(remove_params.result["total_items"], 0)
        self.assertEqual(remove_params.result["total_price"], 0)

    def test_remove_fries(self):
        """Test removing fries from the order."""
        # First add fries
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "fries",
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_food_order(add_params))
        
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
        
        loop.run_until_complete(process_food_order(remove_params))
        
        # Check the result
        self.assertEqual(remove_params.result["status"], "items_updated")
        self.assertEqual(remove_params.result["total_items"], 0)
        self.assertEqual(remove_params.result["total_price"], 0)
