"""
Test script to verify combo conversion and WebSocket updates work correctly.
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

class TestComboWebSocket(unittest.TestCase):
    """Test cases for combo conversion and WebSocket updates."""
    
    def setUp(self):
        """Set up for each test."""
        # Reset the current order session
        from food_ordering import current_order_session
        current_order_session.clear_order()
        
        # Clear WebSocket orders store
        from websocket_server import orders_store
        orders_store.clear()
        
        # Create a new event loop for each test
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()
    
    def test_combo_conversion_with_websocket_update(self):
        """Test that combo conversion works and WebSocket gets updated."""
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
        
        # Check that WebSocket store has the order
        from websocket_server import orders_store
        self.assertEqual(len(orders_store), 1)
        
        print(f"Step 1 - Added chicken burrito: ${add_params.result['total_price']}")
        print(f"WebSocket orders store has {len(orders_store)} orders")
        
        # Step 2: Convert to combo (simulating LLM's incorrect call)
        combo_params = MockFunctionCallParams({
            "items": [  # No action specified - defaults to add_item, but should be smart converted
                {
                    "item_id": "chicken_burrito",
                    "combo": True
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(combo_params))
        
        # Verify the smart conversion worked
        self.assertEqual(combo_params.result["status"], "items_updated")
        self.assertEqual(combo_params.result["total_items"], 1)  # Should still be 1 item
        self.assertTrue(combo_params.result.get("smart_conversion", False))
        
        # Verify correct combo pricing
        expected_combo_price = 11.97  # 8.49 + 2.99 + 1.99 - 1.50
        self.assertAlmostEqual(combo_params.result["total_price"], expected_combo_price, places=2)
        
        # Verify the description shows it's a combo
        self.assertIn("Regular Combo", combo_params.result["items"][0])
        
        # Check that WebSocket store was updated
        self.assertEqual(len(orders_store), 1)  # Should still be 1 order
        
        # Get the order from WebSocket store
        invoice_id = combo_params.result["invoice_id"]
        stored_order = orders_store.get(invoice_id)
        self.assertIsNotNone(stored_order)
        
        # Verify the stored order has correct data
        self.assertEqual(stored_order["type"], "order_update")
        self.assertEqual(len(stored_order["items"]), 1)
        
        stored_item = stored_order["items"][0]
        self.assertEqual(stored_item["item_id"], "chicken_burrito")
        self.assertTrue(stored_item["combo"])
        self.assertEqual(stored_item["combo_type"], "regular_combo")
        self.assertAlmostEqual(stored_item["price"], expected_combo_price, places=2)
        self.assertIn("Regular Combo", stored_item["description"])
        
        print(f"Step 2 - Converted to combo: ${combo_params.result['total_price']}")
        print(f"WebSocket store updated with combo: {stored_item['description']}")
        print(f"Smart conversion flag: {combo_params.result.get('smart_conversion', False)}")
        
        # Verify the backend order session also has correct data
        from food_ordering import current_order_session
        self.assertEqual(len(current_order_session.current_order_items), 1)
        
        session_item = current_order_session.current_order_items[0]
        self.assertEqual(session_item["item_id"], "chicken_burrito")
        self.assertTrue(session_item["combo"])
        self.assertEqual(session_item["combo_type"], "regular_combo")
        self.assertAlmostEqual(session_item["price"], expected_combo_price, places=2)
        self.assertIn("Regular Combo", session_item["description"])
        
        print(f"Backend session also updated correctly: {session_item['description']}")

if __name__ == "__main__":
    unittest.main()
