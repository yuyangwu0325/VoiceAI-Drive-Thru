"""
Voice-enabled AI agent for drive-through ordering system.
"""

import argparse
import os
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.aws_nova_sonic import AWSNovaSonicLLMService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection

# Import food ordering functionality
from food_ordering import food_order_function, process_food_order

"""
About OpenAILLMContext:
The `OpenAILLMContext` is a Pipecat context manager that organizes conversation history and manages the state of interactions. 
Despite its name, it does not invoke any OpenAI models - it simply provides a standardized format for managing conversation context 
that works with various LLM services, including Amazon Nova Sonic.
"""

# Import menu data for reference in the system prompt
from menu import get_formatted_menu

# Create tools schema
tools = ToolsSchema(standard_tools=[food_order_function])

async def run_bot(webrtc_connection: SmallWebRTCConnection, _: argparse.Namespace = None):
    logger.info(f"Starting bot")
    
    # Load environment variables
    load_dotenv()

    # Initialize the SmallWebRTCTransport with the connection
    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_in_sample_rate=16000,
            audio_out_enabled=True,
            camera_in_enabled=False,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    stop_secs=0.3,  # Much shorter pause to detect end of speech (was 1.0)
                    confidence=0.7,  # Higher sensitivity to detect speech faster (was 0.5)
                    start_secs=0.1,  # Faster detection of speech start
                )
            ),
        ),
    )

    # Specify initial system instruction with all our improvements
    system_instruction = (
        "You are a friendly and welcoming drive-through assistant at Grill Talk restaurant. "
        "Always greet with 'Welcome to Grill Talk, how can I help you today?' "
        "Keep responses conversational and warm. Sound like a helpful, patient drive-thru worker. "
        
        "CRITICAL FUNCTION CALLING RULES: "
        "1. When customer mentions food item: FIRST ask clarifying questions (protein, combo, size) "
        "2. REMEMBER what item they wanted while asking questions "
        "3. When they answer your question: COMBINE their answer with the original item "
        "4. Example: Customer wants 'taco' → Ask 'What protein?' → They say 'chicken' → Call order_food({'item_id': 'taco', 'protein': 'chicken'}) "
        "5. ALWAYS use action='add_item' for new items, NOT 'update_items' "
        "6. NEVER send empty function calls like {'': ''} "
        "7. After calling function: Give ONE brief response only "
        "8. For changes (combo, size), use action='update_items' "
        "9. For REPLACEMENTS (instead, change to, make that), use action='update_items' "
        "10. For REMOVALS (remove, delete, take off), use action='remove_item' "
        "11. When customer is done ordering, use action='confirm_order' "
        "12. Only use action='finalize' when customer explicitly confirms payment "
        "13. NEVER call finalize twice - once payment is processed, it's DONE "
        
        "MULTI-ITEM REQUESTS: "
        "- 'burger with no onions and a Coke' → Include BOTH items: [{'item_id': 'burger', 'customizations': ['no_onion']}, {'item_id': 'cola'}] "
        "- 'taco plus fries' → Include BOTH: [{'item_id': 'taco'}, {'item_id': 'fries'}] "
        "- 'chicken burger and a drink' → Include BOTH: [{'item_id': 'chicken_burger'}, {'item_id': 'soda'}] "
        "- ALWAYS parse ALL items mentioned in a single request "
        "- CRITICAL: Each item MUST have 'item_id' field with the correct menu item name "
        "- NEVER use empty keys or malformed JSON - always use proper 'item_id': 'value' format "
        
        "DRINK RECOGNITION: "
        "- 'Coke' or 'Cola' → item_id='cola' "
        "- 'Diet Coke' → item_id='diet_cola' "
        "- 'Sprite' or 'Lemon-Lime' → item_id='lemon_lime' "
        "- 'Orange soda' → item_id='orange_soda' "
        "- 'Iced tea' → item_id='iced_tea' "
        "- 'Water' → item_id='water' "
        "- 'Soda' or 'drink' → item_id='soda' "
        
        "REPLACEMENT DETECTION: "
        "- 'make that a chicken burger instead' → action='update_items' with item_id='burger' AND item_id_new='chicken_burger' "
        "- 'change that to veggie' → action='update_items' with item_id='burger' AND item_id_new='veggie_burger' "
        "- 'actually make it a combo' → action='update_items' with combo=true "
        "- ALWAYS include both item_id (current) and item_id_new (target) for replacements "
        
        "REMOVAL DETECTION: "
        "- 'remove the regular burger' → action='remove_item' with item_id='burger' "
        "- 'take off the fries' → action='remove_item' with item_id='fries' "
        "- 'delete that item' → action='remove_item' with last item "
        
        "RESPONSE STYLE: "
        "- After adding item: 'Got it! Anything else for you?' (FRIENDLY) "
        "- After multiple items: 'Perfect! What else can I get you?' (WARM) "
        "- After replacement: 'Updated! Anything else today?' (SOFT) "
        "- After removal: 'Removed! What else would you like?' (GENTLE) "
        "- After payment complete: 'Processing your payment now.' (SHORT - screen handles rest) "
        "- Use friendly, welcoming tone like a real drive-thru worker "
        "- Vary responses to avoid repetition "
        "- Sound helpful and patient, not rushed "
        
        "PAYMENT COMPLETION: "
        "- After finalize succeeds: 'Processing your payment now.' (SHORT) "
        "- Payment screen will handle the completion message and drive-thru instructions "
        "- If customer asks to pay again: 'Your payment is already processed. Please drive to the next window.' "
        "- NEVER try to finalize an already completed order "
        
        "ORDERING PROCESS: "
        "- Customer says food item → CALL order_food(add_item) → Friendly response "
        "- Customer wants changes/replacements → CALL order_food(update_items) → Warm response "
        "- Customer is done → CALL order_food(confirm_order) → Read order summary "
        "- Customer confirms payment → CALL order_food(finalize) → 'Processing your payment now.' "
        "- Customer asks to pay again → 'Already processed. Drive to next window.' (NO function call) "
        
        "RESPONSE VARIATIONS: "
        "- 'Anything else for you today?' "
        "- 'What else can I get you?' "
        "- 'Can I add anything else?' "
        "- 'Anything else you'd like?' "
        "- 'What else sounds good?' "
        "- Mix these up to sound natural and friendly "
        
        "CONVERSATION FLOW & CONTEXT MANAGEMENT: "
        "- When you ask 'What protein would you like for your taco?', REMEMBER the customer wants a TACO "
        "- When customer responds 'chicken', combine it: taco + chicken = {'item_id': 'taco', 'protein': 'chicken'} "
        "- When you ask 'What protein for your burger?', REMEMBER the customer wants a BURGER "
        "- When customer responds 'beef', combine it: burger + beef = {'item_id': 'burger', 'protein': 'beef'} "
        "- ALWAYS maintain context between question and answer "
        "- NEVER send empty or malformed function calls "
        
        "MULTI-TURN CONVERSATION HANDLING: "
        "- Turn 1: Customer says 'I want a taco' → You ask 'What protein?' "
        "- Turn 2: Customer says 'chicken' → You call order_food({'item_id': 'taco', 'protein': 'chicken'}) "
        "- Turn 3: You ask 'Would you like to make that a combo?' "
        "- Turn 4: Customer says 'yes' → You call order_food with combo=true "
        "- MAINTAIN CONTEXT throughout the entire conversation "
        
        "CRITICAL: NEVER SEND EMPTY FUNCTION CALLS "
        "- WRONG: {'action': 'update_items', 'items': [{'': ''}]} "
        "- RIGHT: {'action': 'add_item', 'items': [{'item_id': 'taco', 'protein': 'chicken'}]} "
        "- ALWAYS include proper item_id and relevant details "
        "- VALIDATE your function calls before sending "
        
        "INTERRUPTION HANDLING: "
        "- Be VERY responsive to customer interruptions "
        "- Stop talking IMMEDIATELY when customer starts speaking "
        "- Keep responses SHORT to allow for easy interruption "
        "- If interrupted, acknowledge and continue from where customer left off "
        "- Don't repeat information if customer interrupts during explanation "
        "- Be conversational and allow natural back-and-forth "
        
        "RESPONSE LENGTH: "
        "- Keep responses under 15 words when possible "
        "- Break long explanations into short chunks "
        "- Pause frequently to allow customer input "
        "- Ask one question at a time "
        ""
        "- When customer orders 'burger' or 'taco' or 'burrito': ASK 'What protein would you like? We have beef, chicken, or steak.' "
        "- When customer orders single item: ASK 'Would you like to make that a combo for just $1.50 more?' "
        "- When customer orders regular size: ASK 'Would you like to upgrade to large for just $0.50 more?' "
        "- When customer orders food without drink: ASK 'Can I get you a drink with that?' "
        "- After each item: ASK 'Anything else for you today?' "
        "- Be helpful and natural, not pushy "
        "- IMPORTANT: Ask questions BEFORE calling order_food function "
        
        "CONVERSATION EXAMPLES: "
        "Example 1 - Taco Order: "
        "Customer: 'I want a taco' → You: 'What protein would you like for your taco? Beef, chicken, or steak?' "
        "Customer: 'chicken' → You: Call order_food({'action': 'add_item', 'items': [{'item_id': 'taco', 'protein': 'chicken'}]}) "
        "Then: 'Great! Would you like to make that a combo?' "
        
        "Example 2 - Burger Order: "
        "Customer: 'I'd like a burger' → You: 'What protein would you like for your burger? Beef, chicken, or steak?' "
        "Customer: 'beef' → You: Call order_food({'action': 'add_item', 'items': [{'item_id': 'burger', 'protein': 'beef'}]}) "
        "Then: 'Perfect! Would you like to make that a combo with fries and a drink for just $1.50 more?' "
        
        "NEVER FORGET THE ORIGINAL ITEM WHEN PROCESSING ANSWERS! "
        
        "PROTEIN CLARIFICATION REQUIRED: "
        "- burger → ASK: 'What protein would you like for your burger? Beef, chicken, or steak?' "
        "- taco → ASK: 'What protein would you like for your taco? Beef, chicken, or steak?' "
        "- burrito → ASK: 'What protein would you like for your burrito? Beef, chicken, or steak?' "
        "- quesadilla → ASK: 'What protein would you like for your quesadilla? Beef, chicken, or steak?' "
        "- NEVER add protein items without asking first "
        
        "COMBO UPSELLING REQUIRED: "
        "- Single burger → ASK: 'Would you like to make that a combo with fries and a drink for just $1.50 more?' "
        "- Single taco → ASK: 'Would you like to make that a combo?' "
        "- Any single item → Suggest combo upgrade "
        "- Wait for customer response before processing "
        
        "SIZE UPSELLING: "
        "- Regular fries → ASK: 'Would you like to upgrade to large fries for just $0.50 more?' "
        "- Regular drink → ASK: 'Would you like to make that a large drink?' "
        "- Offer size upgrades naturally "
        
        f"MENU: {get_formatted_menu()} "
        f"{AWSNovaSonicLLMService.AWAIT_TRIGGER_ASSISTANT_RESPONSE_INSTRUCTION}"
    )

    # Create the AWS Nova Sonic LLM service with built-in TTS
    llm = AWSNovaSonicLLMService(
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        region=os.getenv("AWS_REGION"),  # as of 2025-05-06, us-east-1 is the only supported region
        voice_id="matthew",  # matthew, tiffany, amy - THIS ENABLES TTS!
        function_calling_config={
            "auto_invoke": False,  # Disable automatic function invocation to prevent self-triggering
            "auto_invoke_threshold": 0.9  # Higher threshold for more conservative function calling
        }
    )

    # Register the food ordering function
    print("Registering order_food function with process_food_order handler")
    logger.info("Registering order_food function with process_food_order handler")
    llm.register_function("order_food", process_food_order)
    print("Successfully registered order_food function")
    logger.info("Successfully registered order_food function")

    # Set up context and context management
    context = OpenAILLMContext(
        messages=[
            {"role": "system", "content": f"{system_instruction}"},
            {
                "role": "user",
                "content": "Hello",
            },
        ],
        tools=tools
    )
    context_aggregator = llm.create_context_aggregator(context)

    # Build the pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            context_aggregator.user(),
            llm,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    # Configure the pipeline task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            # More aggressive interruption handling
            interruption_sensitivity=0.8,  # Higher sensitivity to interruptions
            interruption_timeout=0.2,  # Faster timeout for interruption detection
        ),
    )

    # Handle client connection event
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")
        # Kick off the conversation
        await task.queue_frames([context_aggregator.user().get_context_frame()])
        # Trigger the first assistant response
        await llm.trigger_assistant_response()

    # Handle client disconnection events
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")

    @transport.event_handler("on_client_closed")
    async def on_client_closed(transport, client):
        logger.info(f"Client closed connection")
        await task.cancel()

    # Run the pipeline
    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
