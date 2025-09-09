"""
Test script for menu pricing calculations.
"""

import unittest
from menu import MENU_ITEMS, SIZES, COMBOS, calculate_order_price

class TestMenuPricing(unittest.TestCase):
    """Test cases for menu pricing calculations."""
    
    def test_basic_item_pricing(self):
        """Test basic item pricing without customizations."""
        # Test a single burger
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "description": "1x Burger"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 5.99)
        
        # Test multiple burgers
        order_items = [
            {
                "item_id": "burger",
                "quantity": 3,
                "description": "3x Burger"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 17.97)  # 3 * 5.99 = 17.97
        
        # Test different items
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "description": "1x Burger"
            },
            {
                "item_id": "fries",
                "quantity": 1,
                "description": "1x Fries"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 8.98)  # 5.99 + 2.99 = 8.98
    
    def test_size_pricing(self):
        """Test pricing with different sizes."""
        # Test small burger (no additional cost)
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "size": "small",
                "description": "1x Burger (small)"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 5.99)  # 5.99 + 0.00 = 5.99
        
        # Test medium burger
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "size": "medium",
                "description": "1x Burger (medium)"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 7.49)  # 5.99 + 1.50 = 7.49
        
        # Test large burger
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "size": "large",
                "description": "1x Burger (large)"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 8.49)  # 5.99 + 2.50 = 8.49
    
    def test_combo_pricing(self):
        """Test pricing with combo deals."""
        # Test regular combo
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "combo": True,
                "combo_type": "regular_combo",
                "description": "1x Burger - Combo"
            }
        ]
        # Burger (5.99) + Fries (2.99) + Soda (1.99) - Discount (1.50) = 9.47
        self.assertEqual(calculate_order_price(order_items), 9.47)
        
        # Test large combo
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "combo": True,
                "combo_type": "large_combo",
                "description": "1x Burger - Large Combo"
            }
        ]
        # Burger (5.99) + Large Fries (2.99 + 2.50) + Large Soda (1.99 + 2.50) - Discount (2.00) = 13.97
        self.assertEqual(calculate_order_price(order_items), 13.97)
        
        # Test combo with multiple items
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "combo": True,
                "combo_type": "regular_combo",
                "description": "1x Burger - Combo"
            },
            {
                "item_id": "chicken_burger",
                "quantity": 1,
                "description": "1x Chicken Burger"
            }
        ]
        # Combo Burger (9.47) + Chicken Burger (6.49) = 15.96
        self.assertEqual(calculate_order_price(order_items), 15.96)
    
    def test_customization_pricing(self):
        """Test pricing with customizations."""
        # Test extra cheese
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "customizations": ["extra_cheese"],
                "description": "1x Burger - Extra cheese"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 6.74)  # 5.99 + 0.75 = 6.74
        
        # Test multiple customizations
        order_items = [
            {
                "item_id": "burger",
                "quantity": 1,
                "customizations": ["extra_cheese", "extra_sauce", "gluten_free_bun"],
                "description": "1x Burger - Extra cheese, Extra sauce, Gluten-free bun"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 8.74)  # 5.99 + 0.75 + 0.50 + 1.50 = 8.74
        
        # Test taco customizations
        order_items = [
            {
                "item_id": "taco",
                "quantity": 1,
                "customizations": ["beef", "cheese", "salsa"],
                "description": "1x Taco - Beef, Cheese, Salsa"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 5.49)  # 3.99 + 0.75 + 0.50 + 0.25 = 5.49
    
    def test_protein_pricing(self):
        """Test pricing with different protein options."""
        # Test steak upgrade
        order_items = [
            {
                "item_id": "burrito",
                "quantity": 1,
                "protein": "steak",
                "description": "1x Burrito - Steak"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 9.49)  # 7.99 + 1.50 = 9.49
        
        # Test regular protein (no additional cost)
        order_items = [
            {
                "item_id": "burrito",
                "quantity": 1,
                "protein": "chicken",
                "description": "1x Burrito - Grilled Chicken"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 7.99)
    
    def test_complex_order(self):
        """Test pricing with a complex order."""
        order_items = [
            {
                "item_id": "burger",
                "quantity": 2,
                "size": "large",
                "combo": True,
                "combo_type": "large_combo",
                "customizations": ["extra_cheese", "gluten_free_bun"],
                "description": "2x Burger (large) - Large Combo - Extra cheese, Gluten-free bun"
            },
            {
                "item_id": "chicken_burrito",
                "quantity": 1,
                "size": "medium",
                "description": "1x Chicken Burrito (medium)"
            },
            {
                "item_id": "fries",
                "quantity": 1,
                "size": "large",
                "description": "1x Fries (large)"
            }
        ]
        # Large Combo Burger with customizations: (5.99 + 2.50 + 0.75 + 1.50) + (2.99 + 2.50) + (1.99 + 2.50) - 2.00 = 18.72
        # Multiply by 2 for quantity: 18.72 * 2 = 37.44
        # Medium Chicken Burrito: 8.49 + 1.50 = 9.99
        # Large Fries: 2.99 + 2.50 = 5.49
        # Total: 37.44 + 9.99 + 5.49 = 52.92
        self.assertEqual(calculate_order_price(order_items), 52.92)
    
    def test_zero_quantity(self):
        """Test that items with quantity 0 are ignored."""
        order_items = [
            {
                "item_id": "burger",
                "quantity": 0,
                "description": "0x Burger"
            },
            {
                "item_id": "fries",
                "quantity": 1,
                "description": "1x Fries"
            }
        ]
        self.assertEqual(calculate_order_price(order_items), 2.99)  # Only the fries should be counted

if __name__ == "__main__":
    unittest.main()
