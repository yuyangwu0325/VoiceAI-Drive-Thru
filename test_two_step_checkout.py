"""
Test script for the new two-step checkout process.
This verifies that the checkout process now includes:
1. Order confirmation step
2. Payment processing and order clearing
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

class TestTwoStepCheckout(unittest.TestCase):
    """Test cases for the new two-step checkout process."""
    
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
    
    def test_order_confirmation_step(self):
        """Test the new order confirmation step."""
        # Step 1: Add items to order
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 1,
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
        
        # Verify items were added
        self.assertEqual(add_params.result["status"], "items_added")
        self.assertEqual(add_params.result["total_items"], 2)
        
        print(f"Step 1 - Added items: ${add_params.result['total_price']}")
        
        # Step 2: Request order confirmation
        confirm_params = MockFunctionCallParams({
            "action": "confirm_order"
        })
        
        self.loop.run_until_complete(process_food_order(confirm_params))
        
        # Verify order confirmation response
        self.assertEqual(confirm_params.result["status"], "order_confirmation")
        self.assertIn("invoice_id", confirm_params.result)
        self.assertIn("total_price", confirm_params.result)
        self.assertEqual(confirm_params.result["total_items"], 2)
        self.assertIn("Please confirm your order", confirm_params.result["message"])
        
        print(f"Step 2 - Order confirmation: {confirm_params.result['message']}")
        print(f"Items to confirm: {confirm_params.result['items']}")
        print(f"Total: ${confirm_params.result['total_price']}")
        
        # Verify order is still active (not finalized yet)
        from food_ordering import current_order_session
        self.assertTrue(current_order_session.is_order_active)
        self.assertEqual(len(current_order_session.current_order_items), 2)
    
    def test_payment_processing_and_clearing(self):
        """Test the payment processing and order clearing step."""
        # Step 1: Add items to order
        add_params = MockFunctionCallParams({
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
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Step 2: Confirm order
        confirm_params = MockFunctionCallParams({
            "action": "confirm_order"
        })
        
        self.loop.run_until_complete(process_food_order(confirm_params))
        
        # Step 3: Finalize order (payment processing)
        finalize_params = MockFunctionCallParams({
            "action": "finalize"
        })
        
        self.loop.run_until_complete(process_food_order(finalize_params))
        
        # Verify payment processing response
        self.assertEqual(finalize_params.result["status"], "order_finalized")
        self.assertEqual(finalize_params.result["payment_status"], "processing")
        self.assertIn("Processing payment", finalize_params.result["message"])
        self.assertIn("invoice_id", finalize_params.result)
        self.assertIn("total_price", finalize_params.result)
        
        print(f"Step 3 - Payment processing: {finalize_params.result['message']}")
        print(f"Payment status: {finalize_params.result['payment_status']}")
        print(f"Final total: ${finalize_params.result['total_price']}")
        
        # Verify order session is cleared for next customer
        from food_ordering import current_order_session
        self.assertFalse(current_order_session.is_order_active)
        self.assertEqual(len(current_order_session.current_order_items), 0)
        
        print("Order session cleared for next customer")
    
    def test_complete_checkout_workflow(self):
        """Test the complete checkout workflow from order to payment."""
        # Step 1: Add multiple items
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "burger",
                    "quantity": 2,
                    "size": "large",
                    "combo": True,
                    "combo_type": "large_combo",
                    "customizations": ["extra_cheese", "no_mayo"]
                },
                {
                    "item_id": "chicken_burrito",
                    "quantity": 1,
                    "size": "medium",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        initial_total = add_params.result["total_price"]
        print(f"Step 1 - Order total: ${initial_total}")
        
        # Step 2: Confirm order
        confirm_params = MockFunctionCallParams({
            "action": "confirm_order"
        })
        
        self.loop.run_until_complete(process_food_order(confirm_params))
        
        # Verify confirmation matches initial order
        self.assertEqual(confirm_params.result["total_price"], initial_total)
        self.assertEqual(confirm_params.result["status"], "order_confirmation")
        
        print(f"Step 2 - Order confirmed: ${confirm_params.result['total_price']}")
        
        # Step 3: Finalize payment
        finalize_params = MockFunctionCallParams({
            "action": "finalize"
        })
        
        self.loop.run_until_complete(process_food_order(finalize_params))
        
        # Verify payment processing
        self.assertEqual(finalize_params.result["status"], "order_finalized")
        self.assertEqual(finalize_params.result["total_price"], initial_total)
        self.assertEqual(finalize_params.result["payment_status"], "processing")
        
        print(f"Step 3 - Payment processed: ${finalize_params.result['total_price']}")
        
        # Verify order is cleared
        from food_ordering import current_order_session
        self.assertFalse(current_order_session.is_order_active)
        
        print("Complete checkout workflow successful!")
    
    def test_confirm_order_with_no_active_order(self):
        """Test confirm_order action when no order is active."""
        confirm_params = MockFunctionCallParams({
            "action": "confirm_order"
        })
        
        self.loop.run_until_complete(process_food_order(confirm_params))
        
        # Should return error
        self.assertEqual(confirm_params.result["status"], "error")
        self.assertIn("No active order to confirm", confirm_params.result["message"])
        
        print(f"No active order error: {confirm_params.result['message']}")

if __name__ == "__main__":
    unittest.main()
