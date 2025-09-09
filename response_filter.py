"""
Response Filter - Prevents repetitive LLM responses
"""

import time
from typing import List, Optional

class ResponseFilter:
    def __init__(self, similarity_threshold: float = 0.7, time_window: int = 30):
        """
        Initialize response filter
        
        Args:
            similarity_threshold: How similar responses need to be to be considered duplicates (0-1)
            time_window: Time window in seconds to check for duplicates
        """
        self.similarity_threshold = similarity_threshold
        self.time_window = time_window
        self.recent_responses: List[dict] = []
    
    def is_repetitive(self, new_response: str) -> bool:
        """
        Check if the new response is repetitive
        
        Args:
            new_response: The new response to check
            
        Returns:
            True if the response is repetitive, False otherwise
        """
        current_time = time.time()
        
        # Clean old responses outside time window
        self.recent_responses = [
            resp for resp in self.recent_responses 
            if current_time - resp['timestamp'] <= self.time_window
        ]
        
        # Check similarity with recent responses
        for recent in self.recent_responses:
            if self._calculate_similarity(new_response, recent['text']) >= self.similarity_threshold:
                print(f"REPETITIVE RESPONSE DETECTED: '{new_response}' similar to '{recent['text']}'")
                return True
        
        # Add new response to history
        self.recent_responses.append({
            'text': new_response,
            'timestamp': current_time
        })
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0 and 1
        """
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def get_alternative_response(self, repetitive_response: str, context: str = "") -> str:
        """
        Generate an alternative response when repetition is detected
        
        Args:
            repetitive_response: The repetitive response
            context: Context to help generate alternative
            
        Returns:
            Alternative response
        """
        # Simple alternatives for common repetitive patterns
        alternatives = {
            "added": ["Got it!", "Done!", "Perfect!", "Added!"],
            "order": ["Your order", "You've got", "That's"],
            "anything else": ["What else?", "Anything more?", "What else can I get you?"],
            "total": ["That's", "Your total is", "Comes to"]
        }
        
        # Find matching pattern and return alternative
        for pattern, alts in alternatives.items():
            if pattern in repetitive_response.lower():
                # Cycle through alternatives
                alt_index = len(self.recent_responses) % len(alts)
                return alts[alt_index]
        
        # Default short response
        return "Got it!"
    
    def clear_history(self):
        """Clear response history"""
        self.recent_responses = []

# Global instance
response_filter = ResponseFilter()

def filter_response(response: str) -> str:
    """
    Filter response for repetition
    
    Args:
        response: The response to filter
        
    Returns:
        Filtered response (original or alternative)
    """
    if response_filter.is_repetitive(response):
        alternative = response_filter.get_alternative_response(response)
        print(f"RESPONSE FILTERED: '{response}' → '{alternative}'")
        return alternative
    
    return response

# Test the filter
if __name__ == "__main__":
    # Test repetitive responses
    responses = [
        "I've added a burger to your order",
        "Got it, I've added your burger to the order",
        "I've added fries to your order",
        "Got it, I've added your fries to the order"
    ]
    
    for resp in responses:
        filtered = filter_response(resp)
        print(f"Original: {resp}")
        print(f"Filtered: {filtered}")
        print("---")
