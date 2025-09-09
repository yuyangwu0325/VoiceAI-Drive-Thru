# agent.py
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


async def fetch_weather_from_api(params: FunctionCallParams):
    temperature = 75 if params.arguments["format"] == "fahrenheit" else 24
    await params.result_callback(
        {
            "conditions": "nice",
            "temperature": temperature,
            "format": params.arguments["format"],
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        }
    )


weather_function = FunctionSchema(
    name="get_current_weather",
    description="Get the current weather",
    properties={
        "location": {
            "type": "string",
            "description": "The city and state, e.g. San Francisco, CA",
        },
        "format": {
            "type": "string",
            "enum": ["celsius", "fahrenheit"],
            "description": "The temperature unit to use. Infer this from the users location.",
        },
    },
    required=["location", "format"],
)

# Create tools schema
tools = ToolsSchema(standard_tools=[weather_function, food_order_function])


async def run_bot(webrtc_connection: SmallWebRTCConnection, _: argparse.Namespace):
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
                		stop_secs=1.0,  # Longer pause to detect end of speech
                		confidence=0.5,  # Lower sensitivity threshold to detect more speech
            		)
        	),
    	),
    )

    # Specify initial system instruction
    system_instruction = (
        "You are a friendly and welcoming drive-through assistant at Grill Talk restaurant. "
        "Always greet with 'Welcome to Grill Talk, how can I help you today?' "
        "Keep responses conversational and warm. Sound like a helpful, patient drive-thru worker. "
        "CRITICAL FUNCTION CALLING RULES: "
        "1. When customer mentions ANY food item they want to order, IMMEDIATELY call order_food with action='add_item' "
        "2. Do NOT just talk about adding items - actually call the function first "
        "3. After calling the function, give ONE brief response only "
        "4. For changes (combo, size), use action='update_items' "
        "5. For REPLACEMENTS (instead, change to, make that), use action='update_items' "
        "6. For REMOVALS (remove, delete, take off), use action='remove_item' "
        "7. When customer is done ordering, use action='confirm_order' "
        "8. Only use action='finalize' when customer explicitly confirms payment "
        "9. NEVER call finalize twice - once payment is processed, it's DONE "
        "MULTI-ITEM REQUESTS: "
        "- 'burger with no onions and a Coke' → Include BOTH items: [{'item_id': 'burger', 'customizations': ['no_onion']}, {'item_id': 'cola'}] "
        "- 'taco plus fries' → Include BOTH: [{'item_id': 'taco'}, {'item_id': 'fries'}] "
        "- 'chicken burger and a drink' → Include BOTH: [{'item_id': 'chicken_burger'}, {'item_id': 'soda'}] "
        "- ALWAYS parse ALL items mentioned in a single request "
        "DRINK RECOGNITION: "
        "- 'Coke' or 'Cola' → item_id='cola' "
        "- 'Diet Coke' → item_id='diet_cola' "
        "- 'Sprite' or 'Lemon-Lime' → item_id='lemon_lime' "
        "- 'Orange soda' → item_id='orange_soda' "
        "- 'Iced tea' → item_id='iced_tea' "
        "- 'Water' → item_id='water' "
        "- 'Soda' or 'drink' → item_id='soda' "
        "MULTI-ITEM REQUESTS: "
        "- 'burger with no onions and a Coke' → Include BOTH items: [{'item_id': 'burger', 'customizations': ['no_onion']}, {'item_id': 'cola'}] "
        "- 'taco plus fries' → Include BOTH: [{'item_id': 'taco'}, {'item_id': 'fries'}] "
        "- 'chicken burger and a drink' → Include BOTH: [{'item_id': 'chicken_burger'}, {'item_id': 'soda'}] "
        "- ALWAYS parse ALL items mentioned in a single request "
        "PAYMENT COMPLETION: "
        "- After finalize succeeds: 'Processing your payment now.' (SHORT) "
        "- Payment screen will handle the completion message and drive-thru instructions "
        "- If customer asks to pay again: 'Your payment is already processed. Please drive to the next window.' "
        "- NEVER try to finalize an already completed order "
        "        "DRINK RECOGNITION: "
        "- 'Coke' or 'Cola' → item_id='cola' "
        "- 'Diet Coke' → item_id='diet_cola' "
        "- 'Sprite' or 'Lemon-Lime' → item_id='lemon_lime' "
        "- 'Orange soda' → item_id='orange_soda' "
        "- 'Iced tea' → item_id='iced_tea' "
        "- 'Water' → item_id='water' "
        "- 'Soda' or 'drink' → item_id='soda' ""
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
        "UPSELLING: "
        "- Suggest combos naturally: 'Would you like to make that a combo for just $1.50 more?' "
        "- After each item ask warmly: 'Anything else for you today?' "
        "- Be helpful, not pushy: 'Can I get you a drink with that?' "
        f"MENU: {get_formatted_menu()} "
        f"{AWSNovaSonicLLMService.AWAIT_TRIGGER_ASSISTANT_RESPONSE_INSTRUCTION}"
    )

    # Create the AWS Nova Sonic LLM service with improved error handling
    llm = AWSNovaSonicLLMService(
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        region=os.getenv("AWS_REGION"),  # as of 2025-05-06, us-east-1 is the only supported region
        voice_id="matthew",  # matthew, tiffany, amy
        function_calling_config={
            "auto_invoke": False,  # Disable automatic function invocation to prevent self-triggering
            "auto_invoke_threshold": 0.9  # Higher threshold for more conservative function calling
        }
    )

    # Register function for function calls
    llm.register_function("get_current_weather", fetch_weather_from_api)
    llm.register_function("get_current_time", get_time)
    
    # Add logging for food order registration
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


async def get_time(params: FunctionCallParams):
    from zoneinfo import ZoneInfo
    
    timezone = params.arguments.get("timezone", "UTC")
    try:
        # Get current time in the specified timezone
        current_time = datetime.now(ZoneInfo(timezone)).strftime("%H:%M:%S")
        await params.result_callback(
            {
                "time": current_time,
                "timezone": timezone,
            }
        )
    except Exception:
        # Fallback to UTC if timezone is invalid
        current_time = datetime.now(ZoneInfo("UTC")).strftime("%H:%M:%S")
        await params.result_callback(
            {
                "time": current_time,
                "timezone": "UTC",
                "note": f"Using UTC (timezone '{timezone}' not recognized)"
            }
        )

time_function = FunctionSchema(
    name="get_current_time",
    description="Get the current time in a specific timezone",
    properties={
        "timezone": {
            "type": "string",
            "description": "The timezone to get the time for, e.g., UTC, EST, PST",
        },
    },
    required=["timezone"],
)

# Update the tools schema
tools = ToolsSchema(standard_tools=[weather_function, time_function, food_order_function])


async def fetch_weather_from_api(params: FunctionCallParams):
 try:
     location = params.arguments.get("location", "")
     temperature_format = params.arguments.get("format", "celsius")
     
     # In a real implementation, you would call a weather API here
     temperature = 75 if temperature_format == "fahrenheit" else 24
     
     await params.result_callback(
         {
             "conditions": "nice",
             "temperature": temperature,
             "format": temperature_format,
             "location": location,
             "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
         }
     )
 except Exception as e:
     logger.error(f"Error fetching weather: {e}")
     await params.result_callback(
         {
             "error": f"Failed to fetch weather information: {str(e)}",
         }
     )



if __name__ == "__main__":
    from run import main

    main()
