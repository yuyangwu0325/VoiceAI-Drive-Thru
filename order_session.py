import uuid
import time
from datetime import datetime

def generate_unique_invoice_id():
    """Generate a unique invoice ID using timestamp and UUID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}-{unique_id}"

class OrderSession:
    def __init__(self):
        self.current_invoice_id = None
        self.current_order_items = []
        self.is_order_active = False
        self.last_item_added = None
        self.last_item_timestamp = 0
        self.duplicate_threshold = 3.0  # seconds
        
    def start_new_order(self):
        """Generate a unique invoice ID only once per customer"""
        self.current_invoice_id = generate_unique_invoice_id()
        self.current_order_items = []
        self.is_order_active = True
        self.last_item_added = None
        self.last_item_timestamp = 0
        return self.current_invoice_id
    
    def is_duplicate_request(self, item):
        """
        Check if this item is a duplicate of the last item added within the threshold time
        
        Returns:
            tuple: (is_duplicate, existing_item_index)
            - is_duplicate: True if item appears to be a duplicate
            - existing_item_index: Index of the existing item in current_order_items if found, None otherwise
        """
        if not self.last_item_added:
            return False, None
            
        current_time = time.time()
        time_diff = current_time - self.last_item_timestamp
        
        # If the request is within the threshold time window
        if time_diff < self.duplicate_threshold:
            # Check if the item is the same as the last one added
            if (self.last_item_added["item_id"] == item["item_id"] and
                self.last_item_added["size"] == item["size"] and
                self.last_item_added["protein"] == item["protein"]):
                
                # Find the index of the existing item in the order
                for i, order_item in enumerate(self.current_order_items):
                    if (order_item["item_id"] == item["item_id"] and
                        order_item["size"] == item["size"] and
                        order_item["protein"] == item["protein"]):
                        return True, i
                        
        return False, None
        
    def add_item_to_order(self, item):
        """
        Add an item to the current order, handling potential duplicates
        
        Returns:
            tuple: (current_order_items, is_duplicate, action_taken)
            - current_order_items: The updated order items list
            - is_duplicate: Whether the item was detected as a potential duplicate
            - action_taken: Description of the action taken ('added_new', 'increased_quantity')
        """
        if not self.is_order_active:
            self.start_new_order()
            
        is_duplicate, existing_item_index = self.is_duplicate_request(item)
        action_taken = 'added_new'
        
        if is_duplicate and existing_item_index is not None:
            # Increase the quantity of the existing item instead of adding a duplicate
            self.current_order_items[existing_item_index]["quantity"] += item["quantity"]
            
            # Update the description to reflect the new quantity
            quantity = self.current_order_items[existing_item_index]["quantity"]
            description = self.current_order_items[existing_item_index]["description"]
            # Replace the quantity at the beginning of the description
            old_quantity = description.split('x')[0]
            self.current_order_items[existing_item_index]["description"] = description.replace(
                f"{old_quantity}x", f"{quantity}x", 1
            )
            
            # Recalculate the price based on the new quantity
            self.current_order_items[existing_item_index]["price"] = (
                self.current_order_items[existing_item_index]["price"] / 
                (quantity - item["quantity"])
            ) * quantity
            
            action_taken = 'increased_quantity'
        else:
            # Add as a new item
            self.current_order_items.append(item)
            self.last_item_added = item
            self.last_item_timestamp = time.time()
            
        return self.current_order_items, is_duplicate, action_taken
        
    def finalize_order(self):
        """Calculate totals and finalize the order"""
        order_summary = {
            "invoice_id": self.current_invoice_id,
            "items": self.current_order_items,
            "total": sum(item["price"] for item in self.current_order_items),
            "timestamp": datetime.now().isoformat()
        }
        self.is_order_active = False
        return order_summary
        
    def clear_order(self):
        """Reset the order session for a new customer"""
        self.current_invoice_id = None
        self.current_order_items = []
        self.is_order_active = False
        self.last_item_added = None
        self.last_item_timestamp = 0
