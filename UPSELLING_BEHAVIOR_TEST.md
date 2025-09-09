# 🍔 Enhanced Upselling Behavior Test Guide

## **🎯 What Changed**

### **Before (BROKEN):**
- Customer: "I'd like a burger"
- LLM: *Immediately calls order_food and adds basic burger*
- Result: ❌ No protein question, no combo upsell, no interaction

### **After (FIXED):**
- Customer: "I'd like a burger"
- LLM: "What protein would you like for your burger? Beef, chicken, or steak?"
- Customer: "Beef please"
- LLM: "Would you like to make that a combo with fries and a drink for just $1.50 more?"
- Customer: "Yes"
- LLM: *Calls order_food with complete details*
- Result: ✅ Full upselling conversation, complete order

## **🎤 Test Scenarios**

### **Scenario 1: Protein Clarification**
**Say:** "I'd like a burger"
**Expected Response:** "What protein would you like for your burger? Beef, chicken, or steak?"
**Follow-up:** Choose a protein and see combo upsell

### **Scenario 2: Combo Upselling**
**Say:** "I'll take a chicken burger"
**Expected Response:** "Would you like to make that a combo with fries and a drink for just $1.50 more?"
**Follow-up:** Say "yes" to see complete combo processing

### **Scenario 3: Size Upselling**
**Say:** "Can I get regular fries"
**Expected Response:** "Would you like to upgrade to large fries for just $0.50 more?"
**Follow-up:** Test both "yes" and "no" responses

### **Scenario 4: Drink Addition**
**Say:** "I want a taco"
**Expected Responses:** 
1. "What protein would you like for your taco? Beef, chicken, or steak?"
2. "Would you like to make that a combo?"
3. "Can I get you a drink with that?"

### **Scenario 5: Complete Journey**
**Say:** "I'd like a burger"
**Expected Flow:**
1. "What protein would you like? Beef, chicken, or steak?"
2. "Would you like to make that a combo for $1.50 more?"
3. "Anything else for you today?"

## **🔧 Key Improvements**

### **Enhanced LLM Instructions:**
1. **Protein Clarification Required** - Must ask before adding protein items
2. **Combo Upselling Required** - Must offer combo upgrades
3. **Size Upselling** - Must offer size upgrades
4. **Function Calling Order** - Ask questions BEFORE calling order_food
5. **Natural Conversation** - Friendly, helpful, not pushy

### **Specific Prompts Added:**
- "What protein would you like for your burger? Beef, chicken, or steak?"
- "Would you like to make that a combo with fries and a drink for just $1.50 more?"
- "Would you like to upgrade to large fries for just $0.50 more?"
- "Can I get you a drink with that?"
- "Anything else for you today?"

## **🎉 Expected Behavior**

### **When You Say "burger":**
1. ✅ LLM asks about protein options
2. ✅ LLM asks about combo upgrade
3. ✅ LLM asks about additional items
4. ✅ Only then calls order_food with complete details
5. ✅ Creates proper order with all selections

### **Natural Conversation Flow:**
- Customer feels engaged and guided
- All options are presented clearly
- Upselling feels helpful, not pushy
- Complete orders with proper details
- Higher average order value through natural suggestions

## **🚀 Ready to Test!**

**Start with:** "I'd like a burger"

You should now hear the LLM ask about protein options instead of immediately adding a basic burger to your order!

**Expected Response:** "What protein would you like for your burger? Beef, chicken, or steak?"
