"""
Test script for the transcription WebSocket.
"""

import asyncio
import websockets
import json

async def test_transcription_websocket():
    """Test the transcription WebSocket connection."""
    uri = "ws://localhost:7860/transcription"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))
            print("Sent ping")
            
            # Wait for a response
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Keep the connection open for a while
            for i in range(5):
                await asyncio.sleep(1)
                print(f"Waiting... {i+1}/5")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_transcription_websocket())
