"""
Order history tracking for the GrillTalk system.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

# Define the path for storing order history
HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "order_history")

# Create the directory if it doesn't exist
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

class OrderHistory:
    def __init__(self):
        self.history_cache = {}
        self.load_history()
        
    def load_history(self):
        """Load order history from disk."""
        try:
            # Load all JSON files in the history directory
            for filename in os.listdir(HISTORY_DIR):
                if filename.endswith(".json"):
                    file_path = os.path.join(HISTORY_DIR, filename)
                    with open(file_path, "r") as f:
                        order_data = json.load(f)
                        invoice_id = order_data.get("invoice_id")
                        if invoice_id:
                            self.history_cache[invoice_id] = order_data
            
            logger.info(f"Loaded {len(self.history_cache)} orders from history")
        except Exception as e:
            logger.error(f"Error loading order history: {e}")
    
    def save_order(self, order_data: Dict):
        """Save an order to history."""
        try:
            invoice_id = order_data.get("invoice_id")
            if not invoice_id:
                logger.error("Cannot save order without invoice_id")
                return False
            
            # Add timestamp if not present
            if "timestamp" not in order_data:
                order_data["timestamp"] = datetime.now().isoformat()
            
            # Save to cache
            self.history_cache[invoice_id] = order_data
            
            # Save to disk
            file_path = os.path.join(HISTORY_DIR, f"{invoice_id}.json")
            with open(file_path, "w") as f:
                json.dump(order_data, f, indent=2)
            
            logger.info(f"Order {invoice_id} saved to history")
            return True
        except Exception as e:
            logger.error(f"Error saving order to history: {e}")
            return False
    
    def get_order(self, invoice_id: str) -> Optional[Dict]:
        """Get an order from history by invoice ID."""
        return self.history_cache.get(invoice_id)
    
    def get_recent_orders(self, limit: int = 10) -> List[Dict]:
        """Get the most recent orders."""
        # Sort orders by timestamp (newest first)
        sorted_orders = sorted(
            self.history_cache.values(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        # Return the specified number of orders
        return sorted_orders[:limit]
    
    def search_orders(self, query: str) -> List[Dict]:
        """Search orders by invoice ID or item description."""
        results = []
        query = query.lower()
        
        for order in self.history_cache.values():
            # Check invoice ID
            if query in order.get("invoice_id", "").lower():
                results.append(order)
                continue
            
            # Check items
            items = order.get("items", [])
            for item in items:
                if isinstance(item, dict) and query in item.get("description", "").lower():
                    results.append(order)
                    break
                elif isinstance(item, str) and query in item.lower():
                    results.append(order)
                    break
        
        return results
    
    def delete_order(self, invoice_id: str) -> bool:
        """Delete an order from history."""
        try:
            if invoice_id in self.history_cache:
                # Remove from cache
                del self.history_cache[invoice_id]
                
                # Remove from disk
                file_path = os.path.join(HISTORY_DIR, f"{invoice_id}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                logger.info(f"Order {invoice_id} deleted from history")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting order from history: {e}")
            return False
    
    def clear_history(self) -> bool:
        """Clear all order history."""
        try:
            # Clear cache
            self.history_cache = {}
            
            # Clear disk
            for filename in os.listdir(HISTORY_DIR):
                if filename.endswith(".json"):
                    os.remove(os.path.join(HISTORY_DIR, filename))
            
            logger.info("Order history cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing order history: {e}")
            return False

# Create a global instance of OrderHistory
order_history = OrderHistory()
