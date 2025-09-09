"""
Test script for order processing functionality.
"""

import unittest
import json
from order_session import OrderSession
from menu import calculate_order_price

class TestOrderProcessing(unittest.TestCase):
    """Test cases for order processing functionality."""
    
    def setUp(self):
        """Set up a new order session for each test."""
        self.order_session = OrderSession()
    
    def test_start_new_order(self):
        """Test starting a new order."""
        invoice_id = self.order_session.start_new_order()
        self.assertIsNotNone(invoice_id)
        self.assertTrue(self.order_session.is_order_active)
        self.assertEqual(len(self.order_session.current_order_items), 0)
    
    def test_add_item_to_order(self):
        """Test adding an item to an order."""
        # Start a new order
        self.order_session.start_new_order()
        
        # Add a burger to the order
        item = {
            "item_id": "burger",
            "quantity": 1,
            "price": 5.99,
            "description": "1x Burger"
        }
        
        updated_items, is_duplicate, action_taken = self.order_session.add_item_to_order(item)
        
        # Check that the item was added
        self.assertEqual(len(updated_items), 1)
        self.assertEqual(updated_items[0]["item_id"], "burger")
        self.assertEqual(updated_items[0]["quantity"], 1)
        self.assertFalse(is_duplicate)
        self.assertEqual(action_taken, "added_new")
    
    def test_duplicate_detection(self):
        """Test duplicate item detection."""
        # Start a new order
        self.order_session.start_new_order()
        
        # Add a burger to the order
        item1 = {
            "item_id": "burger",
            "quantity": 1,
            "price": 5.99,
            "description": "1x Burger"
        }
        
        self.order_session.add_item_to_order(item1)
        
        # Add the same burger again quickly
        item2 = {
            "item_id": "burger",
            "quantity": 1,
            "price": 5.99,
            "description": "1x Burger"
        }
        
        # Manually set the last_item_timestamp to simulate a quick duplicate request
        self.order_session.last_item_timestamp = self.order_session.last_item_timestamp - 1.0
        
        updated_items, is_duplicate, action_taken = self.order_session.add_item_to_order(item2)
        
        # Check that the item was detected as a duplicate and the quantity was increased
        self.assertEqual(len(updated_items), 1)
        self.assertEqual(updated_items[0]["item_id"], "burger")
        self.assertEqual(updated_items[0]["quantity"], 2)
        self.assertTrue(is_duplicate)
        self.assertEqual(action_taken, "increased_quantity")
    
    def test_finalize_order(self):
        """Test finalizing an order."""
        # Start a new order
        invoice_id = self.order_session.start_new_order()
        
        # Add items to the order
        item1 = {
            "item_id": "burger",
            "quantity": 1,
            "price": 5.99,
            "description": "1x Burger"
        }
        
        item2 = {
            "item_id": "fries",
            "quantity": 1,
            "price": 2.99,
            "description": "1x Fries"
        }
        
        self.order_session.add_item_to_order(item1)
        self.order_session.add_item_to_order(item2)
        
        # Finalize the order
        order_summary = self.order_session.finalize_order()
        
        # Check the order summary
        self.assertEqual(order_summary["invoice_id"], invoice_id)
        self.assertEqual(len(order_summary["items"]), 2)
        self.assertEqual(order_summary["total"], 8.98)  # 5.99 + 2.99 = 8.98
        self.assertFalse(self.order_session.is_order_active)
    
    def test_clear_order(self):
        """Test clearing an order."""
        # Start a new order
        self.order_session.start_new_order()
        
        # Add an item to the order
        item = {
            "item_id": "burger",
            "quantity": 1,
            "price": 5.99,
            "description": "1x Burger"
        }
        
        self.order_session.add_item_to_order(item)
        
        # Clear the order
        self.order_session.clear_order()
        
        # Check that the order was cleared
        self.assertIsNone(self.order_session.current_invoice_id)
        self.assertEqual(len(self.order_session.current_order_items), 0)
        self.assertFalse(self.order_session.is_order_active)
    
    def test_add_item_to_inactive_order(self):
        """Test adding an item to an inactive order."""
        # Don't start a new order
        
        # Add an item to the order
        item = {
            "item_id": "burger",
            "quantity": 1,
            "price": 5.99,
            "description": "1x Burger"
        }
        
        updated_items, is_duplicate, action_taken = self.order_session.add_item_to_order(item)
        
        # Check that a new order was started automatically
        self.assertTrue(self.order_session.is_order_active)
        self.assertEqual(len(updated_items), 1)
        self.assertEqual(updated_items[0]["item_id"], "burger")
        self.assertEqual(action_taken, "added_new")

if __name__ == "__main__":
    unittest.main()
