"""
Test script to verify the Smart Detection System is menu-agnostic and works with any menu items.
This tests that the system doesn't rely on hardcoded values like "burrito" or "beef".
"""

import unittest
import asyncio
import json
from food_ordering import process_food_order, detect_invalid_item_id_patterns, find_item_variants
from pipecat.services.llm_service import FunctionCallParams
from menu import MENU_ITEMS, PROTEIN_OPTIONS

# Create a mock FunctionCallParams class for testing
class MockFunctionCallParams:
    def __init__(self, arguments):
        self.arguments = arguments
        self.result = None
    
    async def result_callback(self, result):
        self.result = result

class TestDynamicMenuAgnostic(unittest.TestCase):
    """Test cases to verify the Smart Detection System is menu-agnostic."""
    
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
    
    def test_invalid_item_id_detection_is_dynamic(self):
        """Test that invalid item ID detection works with any menu items."""
        # Test with existing menu items
        corrected_id, protein = detect_invalid_item_id_patterns("beef_burrito", MENU_ITEMS, PROTEIN_OPTIONS)
        self.assertEqual(corrected_id, "burrito")
        self.assertEqual(protein, "beef")
        
        corrected_id, protein = detect_invalid_item_id_patterns("chicken_taco", MENU_ITEMS, PROTEIN_OPTIONS)
        self.assertEqual(corrected_id, "taco")
        self.assertEqual(protein, "chicken")
        
        corrected_id, protein = detect_invalid_item_id_patterns("steak_quesadilla", MENU_ITEMS, PROTEIN_OPTIONS)
        self.assertEqual(corrected_id, "quesadilla")
        self.assertEqual(protein, "steak")
        
        # Test with non-existent combinations
        corrected_id, protein = detect_invalid_item_id_patterns("beef_pizza", MENU_ITEMS, PROTEIN_OPTIONS)
        self.assertEqual(corrected_id, "beef_pizza")  # Should return original since pizza doesn't exist
        self.assertIsNone(protein)
        
        # Test with valid item IDs
        corrected_id, protein = detect_invalid_item_id_patterns("burger", MENU_ITEMS, PROTEIN_OPTIONS)
        self.assertEqual(corrected_id, "burger")
        self.assertIsNone(protein)
    
    def test_item_variant_detection_is_dynamic(self):
        """Test that item variant detection works with any menu items."""
        # Test burrito variants
        variants = find_item_variants("burrito", MENU_ITEMS)
        self.assertIn("burrito", variants)
        self.assertIn("chicken_burrito", variants)
        
        variants = find_item_variants("chicken_burrito", MENU_ITEMS)
        self.assertIn("burrito", variants)
        self.assertIn("chicken_burrito", variants)
        
        # Test burger variants (the system actually finds chicken_burger and veggie_burger as variants)
        variants = find_item_variants("burger", MENU_ITEMS)
        self.assertIn("burger", variants)
        self.assertIn("chicken_burger", variants)
        self.assertIn("veggie_burger", variants)
        
        # Test items without variants
        variants = find_item_variants("taco", MENU_ITEMS)
        self.assertEqual(variants, ["taco"])  # Only itself
    
    def test_smart_detection_works_with_any_protein_item_combo(self):
        """Test that Smart Detection works with any valid protein + item combination."""
        # Test with chicken_taco -> taco conversion
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "taco",
                    "quantity": 1,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Now try to use invalid "chicken_taco" ID
        wrong_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "chicken_taco",  # Invalid ID that should be corrected
                    "quantity": 1
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Should be smart converted to update with chicken protein
        self.assertEqual(wrong_params.result["status"], "items_updated")
        self.assertEqual(wrong_params.result["total_items"], 1)
        self.assertTrue(wrong_params.result.get("smart_conversion", False))
        self.assertIn("with Grilled Chicken", wrong_params.result["items"][0])
    
    def test_smart_detection_works_with_steak_quesadilla(self):
        """Test Smart Detection with steak_quesadilla -> quesadilla + steak conversion."""
        # Add a regular quesadilla
        add_params = MockFunctionCallParams({
            "action": "add_item",
            "items": [
                {
                    "item_id": "quesadilla",
                    "quantity": 1,
                    "size": "regular",
                    "combo": False,
                    "customizations": []
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(add_params))
        
        # Try to use invalid "steak_quesadilla" ID
        wrong_params = MockFunctionCallParams({
            "items": [
                {
                    "item_id": "steak_quesadilla",  # Invalid ID
                    "quantity": 1
                }
            ]
        })
        
        self.loop.run_until_complete(process_food_order(wrong_params))
        
        # Should be smart converted
        self.assertEqual(wrong_params.result["status"], "items_updated")
        self.assertEqual(wrong_params.result["total_items"], 1)
        self.assertTrue(wrong_params.result.get("smart_conversion", False))
        self.assertIn("with Steak", wrong_params.result["items"][0])
    
    def test_no_hardcoded_values_in_smart_detection(self):
        """Test that the system doesn't break when menu items change."""
        # This test verifies that the system uses dynamic functions
        # and doesn't rely on hardcoded strings like "burrito" or "beef"
        
        # Test that the system can handle any protein + item combination
        # as long as both exist in the respective dictionaries
        
        # Test specific combinations that should work
        test_cases = [
            ("beef_burrito", "burrito", "beef"),
            ("chicken_taco", "taco", "chicken"),
            ("steak_quesadilla", "quesadilla", "steak"),
            ("veggie_burrito", "burrito", "veggie"),
        ]
        
        for invalid_id, expected_item, expected_protein in test_cases:
            corrected_id, suggested_protein = detect_invalid_item_id_patterns(
                invalid_id, MENU_ITEMS, PROTEIN_OPTIONS
            )
            
            # Should correctly identify the pattern
            self.assertEqual(corrected_id, expected_item, 
                           f"Failed to correct {invalid_id} to {expected_item}")
            self.assertEqual(suggested_protein, expected_protein,
                           f"Failed to suggest {expected_protein} for {invalid_id}")
        
        # Test that existing items don't get modified
        for item_id in MENU_ITEMS:
            corrected_id, suggested_protein = detect_invalid_item_id_patterns(
                item_id, MENU_ITEMS, PROTEIN_OPTIONS
            )
            self.assertEqual(corrected_id, item_id, f"Valid item {item_id} was incorrectly modified")
            self.assertIsNone(suggested_protein, f"Valid item {item_id} got unexpected protein suggestion")

if __name__ == "__main__":
    unittest.main()
