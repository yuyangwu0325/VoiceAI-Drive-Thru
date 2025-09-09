import argparse
import asyncio
import importlib.util
import os
import sys
import websockets
from contextlib import asynccontextmanager
from datetime import datetime
from inspect import iscoroutinefunction, signature
from typing import Any, Callable, Dict, Optional, Tuple, Set

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
# Keep the import for compatibility but we won't mount it
from pipecat_ai_small_webrtc_prebuilt.frontend import SmallWebRTCPrebuiltUI

from pipecat.transports.network.webrtc_connection import IceServer, SmallWebRTCConnection

# Import WebSocket server
try:
    from websocket_server import websocket_handler
    WEBSOCKET_ENABLED = True
except ImportError:
    logger.warning("WebSocket server module not found. Order broadcasting disabled.")
    WEBSOCKET_ENABLED = False

# Import API endpoints
try:
    from api_endpoints import router as api_router
    API_ENABLED = True
except ImportError:
    logger.warning("API endpoints module not found. API disabled.")
    API_ENABLED = False

# Load environment variables
load_dotenv(override=True)

app = FastAPI()

# Store active transcription WebSocket connections
active_transcription_connections: Set[WebSocket] = set()

# Mount API router if enabled
if API_ENABLED:
    app.include_router(api_router)
    logger.info("API endpoints mounted")

# Store connections by pc_id
pcs_map: Dict[str, SmallWebRTCConnection] = {}

ice_servers = [
    IceServer(
        urls="stun:stun.l.google.com:19302",
    )
]

# Mount the React frontend static files
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

# Mount the images directory
app.mount("/images", StaticFiles(directory="frontend/build/images"), name="images")

# Mount any other static assets at the root level
for static_file in os.listdir("frontend/build"):
    if static_file != "static" and static_file != "images" and os.path.isfile(os.path.join("frontend/build", static_file)):
        @app.get(f"/{static_file}")
        async def serve_static_file(static_file=static_file):
            return FileResponse(f"frontend/build/{static_file}")

# Store program arguments
args: argparse.Namespace = argparse.Namespace()

# Store the bot module and function info
bot_module: Any = None
run_bot_func: Optional[Callable] = None
is_webrtc_bot: bool = True

def import_bot_file(file_path: str) -> Tuple[Any, Callable, bool]:
    """Dynamically import the bot file and determine how to run it.

    Returns:
        tuple: (module, run_function, is_webrtc_bot)
          - module: The imported module
          - run_function: Either run_bot or main function
          - is_webrtc_bot: True if run_bot function exists and accepts a WebRTC connection
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Bot file not found: {file_path}")

    # Extract module name without extension
    module_name = os.path.splitext(os.path.basename(file_path))[0]

    # Load the module
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not load spec for {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # Check for run_bot function first
    if hasattr(module, "run_bot"):
        run_func = module.run_bot
        # Check if the function accepts a WebRTC connection
        sig = signature(run_func)
        is_webrtc = len(sig.parameters) > 0
        return module, run_func, is_webrtc

    # Fall back to main function
    if hasattr(module, "main") and iscoroutinefunction(module.main):
        return module, module.main, False

    raise AttributeError(f"No run_bot or async main function found in {file_path}")

@app.websocket("/transcription")
async def transcription_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Transcription WebSocket client connected")
    
    # Add to active connections
    active_transcription_connections.add(websocket)
    
    try:
        # Keep the connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Transcription WebSocket client disconnected")
        active_transcription_connections.remove(websocket)
    except Exception as e:
        logger.error(f"Error in transcription WebSocket: {e}")
        if websocket in active_transcription_connections:
            active_transcription_connections.remove(websocket)

async def broadcast_transcription(text: str, is_final: bool = False):
    """Broadcast transcription to all connected clients."""
    if not active_transcription_connections:
        return
    
    message = {
        "type": "transcription",
        "text": text,
        "isFinal": is_final,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.debug(f"Broadcasting transcription: {text} (final: {is_final})")
    
    for connection in list(active_transcription_connections):
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error sending transcription: {e}")
            if connection in active_transcription_connections:
                active_transcription_connections.remove(connection)

@app.get("/", include_in_schema=False)
async def root_redirect():
    return FileResponse("frontend/build/index.html")

@app.get("/{path:path}")
async def serve_react(path: str):
    # Skip API paths
    if path.startswith("api/"):
        raise HTTPException(status_code=404)
    
    # Serve the React app for all other paths
    return FileResponse("frontend/build/index.html")

@app.post("/api/offer")
async def offer(request: dict, background_tasks: BackgroundTasks):
    global run_bot_func, is_webrtc_bot

    if not run_bot_func:
        raise RuntimeError("No bot file has been loaded")

    if not is_webrtc_bot:
        return {
            "error": "This bot doesn't support WebRTC connections, it's running in standalone mode"
        }

    pc_id = request.get("pc_id")

    if pc_id and pc_id in pcs_map:
        pipecat_connection = pcs_map[pc_id]
        logger.info(f"Reusing existing connection for pc_id: {pc_id}")
        await pipecat_connection.renegotiate(
            sdp=request["sdp"], type=request["type"], restart_pc=request.get("restart_pc", False)
        )
    else:
        pipecat_connection = SmallWebRTCConnection(ice_servers)
        await pipecat_connection.initialize(sdp=request["sdp"], type=request["type"])

        @pipecat_connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Discarding peer connection for pc_id: {webrtc_connection.pc_id}")
            try:
                pcs_map.pop(webrtc_connection.pc_id, None)
                logger.info(f"Successfully removed connection from pcs_map")
            except Exception as e:
                logger.error(f"Error removing connection from pcs_map: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # We've already checked that run_bot_func exists
        assert run_bot_func is not None
        background_tasks.add_task(run_bot_func, pipecat_connection, args)

    answer = pipecat_connection.get_answer()
    # Updating the peer connection inside the map
    pcs_map[answer["pc_id"]] = pipecat_connection

    return answer

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # Run app
    coros = [pc.close() for pc in pcs_map.values()]
    await asyncio.gather(*coros)
    pcs_map.clear()


async def run_standalone_bot() -> None:
    """Run a standalone bot that doesn't require WebRTC"""
    global run_bot_func
    if run_bot_func is not None:
        await run_bot_func()
    else:
        raise RuntimeError("No bot function available to run")


def main(parser: Optional[argparse.ArgumentParser] = None):
    global args

    if not parser:
        parser = argparse.ArgumentParser(description="Pipecat Bot Runner")
    parser.add_argument("bot_file", nargs="?", help="Path to the bot file", default=None)
    parser.add_argument(
        "--host", default="localhost", help="Host for HTTP server (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=7860, help="Port for HTTP server (default: 7860)"
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    args = parser.parse_args()

    logger.remove(0)
    if args.verbose:
        logger.add(sys.stderr, level="TRACE")
    else:
        logger.add(sys.stderr, level="DEBUG")

    # Infer the bot file from the caller if not provided explicitly
    bot_file = args.bot_file
    if bot_file is None:
        # Get the __file__ of the script that called main()
        import inspect

        caller_frame = inspect.stack()[1]
        caller_globals = caller_frame.frame.f_globals
        bot_file = caller_globals.get("__file__")

    if not bot_file:
        print("❌ Could not determine the bot file. Pass it explicitly to main().")
        sys.exit(1)

    # Import the bot file
    try:
        global run_bot_func, bot_module, is_webrtc_bot
        bot_module, run_bot_func, is_webrtc_bot = import_bot_file(bot_file)
        logger.info(f"Successfully loaded bot from {bot_file}")

        if is_webrtc_bot:
            logger.info("Detected WebRTC-compatible bot, starting web server...")
            
            # Start WebSocket server in the background if enabled
            if WEBSOCKET_ENABLED:
                # Import necessary modules
                import threading
                import websockets
                
                # Function to run WebSocket server in a separate thread
                def run_websocket_server():
                    # Create a new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Define a coroutine to start the server
                    async def start_server():
                        # Create a wrapper function that provides the path parameter
                        async def handler_wrapper(websocket):
                            await websocket_handler(websocket, "/")
                        
                        ws_port = 8766  # Changed from 8765 to avoid conflicts
                        
                        # Log that we're about to start the server
                        print(f"Starting WebSocket server on port {ws_port}...")
                        logger.info(f"Starting WebSocket server on port {ws_port}...")
                        
                        try:
                            # Start the heartbeat monitor
                            from websocket_server import heartbeat_monitor
                            asyncio.create_task(heartbeat_monitor())
                            logger.info("Started WebSocket heartbeat monitor")
                            
                            server = await websockets.serve(
                                handler_wrapper, 
                                "0.0.0.0",  # Listen on all interfaces
                                ws_port,
                                # Add CORS support
                                origins=None  # Allow all origins
                            )
                            print(f"WebSocket server started successfully on ws://0.0.0.0:{ws_port}")
                            logger.info(f"WebSocket server started successfully on ws://0.0.0.0:{ws_port}")
                            await asyncio.Future()  # Run forever
                        except Exception as e:
                            print(f"Failed to start WebSocket server: {e}")
                            logger.error(f"Failed to start WebSocket server: {e}")
                            import traceback
                            print(traceback.format_exc())
                            logger.error(traceback.format_exc())
                    
                    # Start the server
                    try:
                        loop.run_until_complete(start_server())
                    except Exception as e:
                        logger.error(f"WebSocket server error: {e}")
                    finally:
                        loop.close()
                
                # Start the WebSocket server in a separate thread
                ws_thread = threading.Thread(target=run_websocket_server, daemon=True)
                ws_thread.start()
                logger.info("WebSocket server thread started")
            
            # Start the main web server
            uvicorn.run(app, host=args.host, port=args.port)
        else:
            logger.info("Detected standalone bot, running directly...")
            asyncio.run(run_standalone_bot())
    except Exception as e:
        logger.error(f"Error loading bot file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
