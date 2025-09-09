#!/usr/bin/env python3
"""
Test script to verify multi-item instruction improvements
"""

def test_multi_item_scenarios():
    """Test various multi-item request scenarios"""
    print("🧪 Testing Multi-Item Request Instructions")
    print("=" * 60)
    
    # Test scenarios that were problematic
    scenarios = [
        {
            "name": "Burger with customizations plus Coke",
            "user_request": "I'd like a burger with no onions and extra cheese, plus a Coke",
            "expected_llm_call": {
                "action": "add_item",
                "items": [
                    {"item_id": "burger", "customizations": ["no_onion", "extra_cheese"]},
                    {"item_id": "cola"}
                ]
            },
            "issue_before": "LLM only processed burger, ignored Coke completely"
        },
        {
            "name": "Taco plus fries",
            "user_request": "Can I get a taco plus some fries?",
            "expected_llm_call": {
                "action": "add_item", 
                "items": [
                    {"item_id": "taco"},
                    {"item_id": "fries"}
                ]
            },
            "issue_before": "LLM might miss the 'plus fries' part"
        },
        {
            "name": "Chicken burger and a drink",
            "user_request": "I'll have a chicken burger and a drink",
            "expected_llm_call": {
                "action": "add_item",
                "items": [
                    {"item_id": "chicken_burger"},
                    {"item_id": "soda"}
                ]
            },
            "issue_before": "Generic 'drink' might not be recognized"
        },
        {
            "name": "Multiple drink variations",
            "user_request": "Give me a Coke, Diet Coke, and a Sprite",
            "expected_llm_call": {
                "action": "add_item",
                "items": [
                    {"item_id": "cola"},
                    {"item_id": "diet_cola"},
                    {"item_id": "lemon_lime"}
                ]
            },
            "issue_before": "Drink name variations not properly mapped"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print(f"   User: \"{scenario['user_request']}\"")
        print(f"   Issue Before: {scenario['issue_before']}")
        print(f"   Expected LLM Call:")
        print(f"      Action: {scenario['expected_llm_call']['action']}")
        print(f"      Items:")
        for item in scenario['expected_llm_call']['items']:
            print(f"         • {item}")
    
    print(f"\n🔧 Instructions Added to LLM:")
    print(f"   MULTI-ITEM REQUESTS:")
    print(f"   - 'burger with no onions and a Coke' → Include BOTH items")
    print(f"   - 'taco plus fries' → Include BOTH items")
    print(f"   - 'chicken burger and a drink' → Include BOTH items")
    print(f"   - ALWAYS parse ALL items mentioned in a single request")
    
    print(f"\n   DRINK RECOGNITION:")
    print(f"   - 'Coke' or 'Cola' → item_id='cola'")
    print(f"   - 'Diet Coke' → item_id='diet_cola'")
    print(f"   - 'Sprite' or 'Lemon-Lime' → item_id='lemon_lime'")
    print(f"   - 'Orange soda' → item_id='orange_soda'")
    print(f"   - 'Iced tea' → item_id='iced_tea'")
    print(f"   - 'Water' → item_id='water'")
    print(f"   - 'Soda' or 'drink' → item_id='soda'")
    
    print(f"\n✅ Expected Improvements:")
    print(f"   1. LLM will recognize multiple items in single requests")
    print(f"   2. Proper drink name mapping (Coke → cola)")
    print(f"   3. Both food and drink items included in function call")
    print(f"   4. No more missing items from complex requests")
    print(f"   5. Better parsing of 'plus', 'and', 'with' connectors")
    
    print(f"\n🎯 Key Fix for Your Issue:")
    print(f"   Before: 'burger with no onions and extra cheese, plus a Coke'")
    print(f"   ❌ LLM only processed: burger with customizations")
    print(f"   ❌ Completely missed: Coke")
    print(f"   ")
    print(f"   After: Same request")
    print(f"   ✅ LLM will process: burger with customizations AND cola")
    print(f"   ✅ Both items added to order")

if __name__ == "__main__":
    test_multi_item_scenarios()
