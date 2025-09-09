#!/usr/bin/env python3
"""
Test script to verify WebSocket connection stability.
"""

import asyncio
import websockets
import json
import time

async def test_websocket_connection():
    """Test WebSocket connection stability."""
    uri = "ws://localhost:8766"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Send initial ping
            await websocket.send(json.dumps({"type": "ping"}))
            print("📤 Sent initial ping")
            
            # Listen for messages for 60 seconds
            start_time = time.time()
            while time.time() - start_time < 60:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    print(f"📥 Received: {data.get('type', 'unknown')}")
                    
                    # Respond to pings
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                        print("📤 Sent pong response")
                        
                except asyncio.TimeoutError:
                    # Send periodic ping to keep connection alive
                    await websocket.send(json.dumps({"type": "ping"}))
                    print("📤 Sent keepalive ping")
                    
            print("✅ Connection remained stable for 60 seconds")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing WebSocket connection stability...")
    asyncio.run(test_websocket_connection())
