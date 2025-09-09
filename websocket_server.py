"""
WebSocket server for broadcasting order data to connected clients.
"""

import asyncio
import json
import websockets
from datetime import datetime
from loguru import logger

# Global store for active WebSocket connections
active_connections = set()
# Store for orders that can be accessed by the order processing function
orders_store = {}

async def register(websocket):
    """Register a new WebSocket connection."""
    active_connections.add(websocket)
    print(f"New client connected. Total connections: {len(active_connections)}")
    logger.info(f"New client connected. Total connections: {len(active_connections)}")
    
    # Send a welcome message to confirm the connection is working
    try:
        await websocket.send(json.dumps({"type": "welcome", "message": "Connected to GrillTalk Order Display WebSocket Server"}))
        print("Sent welcome message to new client")
        logger.info("Sent welcome message to new client")
    except Exception as e:
        print(f"Error sending welcome message: {e}")
        logger.error(f"Error sending welcome message: {e}")

async def unregister(websocket):
    """Unregister a WebSocket connection."""
    active_connections.remove(websocket)
    logger.info(f"Client disconnected. Total connections: {len(active_connections)}")

async def broadcast_order(order_data):
    """Broadcast order data to all connected clients."""
    if not active_connections:
        print("No active connections to broadcast order to")
        logger.warning("No active connections to broadcast order to")
        return
    
    # Log the order data for debugging
    print(f"Broadcasting order: {json.dumps(order_data)}")
    logger.info(f"Broadcasting order: {json.dumps(order_data)}")
    print(f"Active connections: {len(active_connections)}")
    logger.info(f"Active connections: {len(active_connections)}")
    
    message = json.dumps(order_data)
    try:
        print(f"Attempting to send order to {len(active_connections)} clients")
        logger.info(f"Attempting to send order to {len(active_connections)} clients")
        for connection in active_connections:
            try:
                await connection.send(message)
                print("Successfully sent order to a client")
                logger.info("Successfully sent order to a client")
            except Exception as e:
                print(f"Error sending to a specific client: {e}")
                logger.error(f"Error sending to a specific client: {e}")
        print(f"Order broadcast completed")
        logger.info(f"Order broadcast completed")
    except Exception as e:
        print(f"Error broadcasting order: {e}")
        logger.error(f"Error broadcasting order: {e}")
        import traceback
        print(traceback.format_exc())
        logger.error(traceback.format_exc())

async def heartbeat_monitor():
    """Monitor connections and send heartbeats to keep them alive."""
    while True:
        if active_connections:
            logger.debug(f"Sending heartbeat to {len(active_connections)} connections")
            heartbeat_message = json.dumps({"type": "heartbeat", "timestamp": datetime.now().isoformat()})
            
            # Create a copy of the set to avoid modification during iteration
            connections = active_connections.copy()
            
            for websocket in connections:
                try:
                    await websocket.send(heartbeat_message)
                except Exception as e:
                    logger.warning(f"Failed to send heartbeat, connection may be dead: {e}")
                    # Connection might be dead, but we'll let the normal error handling take care of it
                    # The connection will be removed when it raises an exception in the main handler
        
        # Wait for 30 seconds before sending the next heartbeat
        await asyncio.sleep(30)

async def websocket_handler(websocket, path):
    """Handle WebSocket connections."""
    print(f"New websocket connection handler called with path: {path}")
    logger.info(f"New websocket connection handler called with path: {path}")
    
    # Register the new connection
    await register(websocket)
    try:
        # Send existing orders to the new client
        if orders_store:
            print(f"Sending {len(orders_store)} existing orders to new client")
            logger.info(f"Sending {len(orders_store)} existing orders to new client")
            for order_id, order in orders_store.items():
                print(f"Sending existing order {order_id} to new client")
                logger.info(f"Sending existing order {order_id} to new client")
                
                # Check if this is a finalized order and send as order_history instead
                if order.get("type") == "order_finalized":
                    # Create a copy of the order with type changed to order_history
                    history_order = order.copy()
                    history_order["type"] = "order_history"
                    await websocket.send(json.dumps(history_order))
                    print(f"Sent order {order_id} as history to avoid duplicate payment screens")
                    logger.info(f"Sent order {order_id} as history to avoid duplicate payment screens")
                else:
                    # Send regular order update
                    await websocket.send(json.dumps(order))
                    print(f"Sent current order {order_id} to new client")
                    logger.info(f"Sent current order {order_id} to new client")
        else:
            print("No existing orders to send to new client")
            logger.info("No existing orders to send to new client")
        
        # Keep the connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages with a timeout to detect disconnections
                message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                
                # Handle any client messages if needed
                print(f"Received message from client: {message}")
                logger.info(f"Received message from client: {message}")
                
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        print("Received ping, sending pong")
                        logger.info("Received ping, sending pong")
                        await websocket.send(json.dumps({"type": "pong"}))
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON message: {message}")
                    
            except asyncio.TimeoutError:
                # Send a ping to check if connection is still alive
                try:
                    await websocket.send(json.dumps({"type": "ping"}))
                    print("Sent ping to check connection")
                    logger.debug("Sent ping to check connection")
                except:
                    print("Connection appears to be dead, breaking")
                    logger.info("Connection appears to be dead, breaking")
                    break
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by client")
                logger.info("Connection closed by client")
                break
                
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")
        logger.info("Connection closed")
    except Exception as e:
        print(f"Error in websocket handler: {e}")
        logger.error(f"Error in websocket handler: {e}")
        import traceback
        print(traceback.format_exc())
        logger.error(traceback.format_exc())
    finally:
        await unregister(websocket)

def start_websocket_server(host="0.0.0.0", port=8765):
    """Start the WebSocket server."""
    return websockets.serve(websocket_handler, host, port)

# Function to be called from food_ordering.py to broadcast new orders
async def publish_order(order_data):
    """Publish a new order to all connected clients."""
    # Store the order
    orders_store[order_data["invoice_id"]] = order_data
    # Log the order data
    print(f"Publishing order: {json.dumps(order_data)}")
    logger.info(f"Publishing order: {json.dumps(order_data)}")
    # Check if there are any active connections
    if not active_connections:
        print(f"No active connections to publish order to. Active connections: {len(active_connections)}")
        logger.warning(f"No active connections to publish order to. Active connections: {len(active_connections)}")
    else:
        print(f"Found {len(active_connections)} active connections to publish order to")
        logger.info(f"Found {len(active_connections)} active connections to publish order to")
    # Broadcast to all clients
    await broadcast_order(order_data)
    return True

async def publish_order_update(invoice_id, items, status="in_progress"):
    """Publish an order update to all connected clients."""
    message = {
        "type": "order_update",
        "invoice_id": invoice_id,
        "items": items,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    print(f"Publishing order update: {json.dumps(message)}")
    logger.info(f"Publishing order update: {json.dumps(message)}")
    
    # Store the current order state
    orders_store[invoice_id] = message
    
    await broadcast_order(message)
    return True

async def publish_final_order(order_summary):
    """Publish a finalized order to all connected clients."""
    message = {
        "type": "order_finalized",
        "order": order_summary,
        "status": "confirmed",
        "timestamp": datetime.now().isoformat()
    }
    print(f"Publishing finalized order: {json.dumps(message)}")
    logger.info(f"Publishing finalized order: {json.dumps(message)}")
    await broadcast_order(message)
    # Update the order in the store
    orders_store[order_summary["invoice_id"]] = message
    return True

async def clear_order(invoice_id):
    """Clear an order from the system."""
    if invoice_id in orders_store:
        del orders_store[invoice_id]
    
    message = {
        "type": "order_cleared",
        "invoice_id": invoice_id,
        "timestamp": datetime.now().isoformat()
    }
    print(f"Clearing order: {json.dumps(message)}")
    logger.info(f"Clearing order: {json.dumps(message)}")
    await broadcast_order(message)
    return True
