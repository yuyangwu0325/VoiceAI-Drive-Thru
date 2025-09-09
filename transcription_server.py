"""
Transcription server for GrillTalk.
This server connects to Nova Sonic and forwards transcription events to the frontend.
"""

import asyncio
import json
import os
import websockets
from loguru import logger
from datetime import datetime

# Store active WebSocket connections
active_connections = set()

async def register(websocket):
    """Register a new WebSocket connection."""
    active_connections.add(websocket)
    logger.info(f"New transcription client connected. Total connections: {len(active_connections)}")
    
    # Send a welcome message to confirm the connection is working
    try:
        await websocket.send(json.dumps({
            "type": "welcome", 
            "message": "Connected to GrillTalk Transcription WebSocket Server"
        }))
        logger.info("Sent welcome message to new transcription client")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

async def unregister(websocket):
    """Unregister a WebSocket connection."""
    active_connections.remove(websocket)
    logger.info(f"Transcription client disconnected. Total connections: {len(active_connections)}")

async def broadcast_transcription(text, is_final=False):
    """Broadcast transcription to all connected clients."""
    if not active_connections:
        logger.warning("No active connections to broadcast transcription to")
        return
    
    message = {
        "type": "transcription",
        "text": text,
        "isFinal": is_final,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.debug(f"Broadcasting transcription: {text} (final: {is_final})")
    
    for connection in list(active_connections):
        try:
            await connection.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending transcription: {e}")
            if connection in active_connections:
                active_connections.remove(connection)

async def websocket_handler(websocket, path):
    """Handle WebSocket connections."""
    logger.info(f"New transcription websocket connection handler called with path: {path}")
    
    # Register the new connection
    await register(websocket)
    try:
        # Keep the connection alive
        while True:
            message = await websocket.recv()
            # Process any messages from the client (like pings)
            try:
                data = json.loads(message)
                if data.get("type") == "ping":
                    logger.info("Received ping, sending pong")
                    await websocket.send(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                logger.warning(f"Received non-JSON message: {message}")
    except websockets.exceptions.ConnectionClosed:
        logger.info("Connection closed")
    except Exception as e:
        logger.error(f"Error in websocket handler: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        await unregister(websocket)

async def start_server(host="0.0.0.0", port=8767):
    """Start the WebSocket server."""
    logger.info(f"Starting transcription WebSocket server on {host}:{port}")
    async with websockets.serve(websocket_handler, host, port):
        await asyncio.Future()  # Run forever

def run_server():
    """Run the WebSocket server in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_server())

if __name__ == "__main__":
    run_server()
