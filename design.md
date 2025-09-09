# GrillTalk: System Design and Architecture

## System Architecture Overview

GrillTalk is designed as a distributed system with the following major components:

1. **Voice Interaction System**: Handles WebRTC communication, speech-to-text, and text-to-speech using Pipecat
2. **Order Processing Engine**: Processes natural language input into structured order data with Smart Detection System
3. **Menu Management System**: Maintains menu items, pricing, and customization options
4. **Real-time Order Display**: Web interface for customers to view their order in real-time
5. **WebSocket Communication Layer**: Enables real-time updates between backend and frontend
6. **Order Session Management**: Manages order state, modifications, and duplicate detection
7. **Smart Detection System**: Automatically corrects LLM function calling errors to prevent customer overcharging

### Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Customer       │     │  Voice           │     │  Order          │
│  WebRTC         │◄───►│  Interaction     │◄───►│  Processing     │
│  Interface      │     │  System (Pipecat)│     │  Engine         │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Customer       │     │  WebSocket      │     │  Smart Detection│
│  Order Display  │◄───►│  Server         │◄───►│  System         │
│  Interface      │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │                       │
                                 ▼                       ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Order Session  │◄───►│  Menu           │
                        │  Management     │     │  Management     │
                        └─────────────────┘     │  System         │
                                                └─────────────────┘
```

## Component Design

### 1. Voice Interaction System

- **WebRTC Integration**: Uses prebuilt WebRTC UI components mounted at "/client" endpoint
- **Speech Processing**: Leverages AWS Nova Sonic for speech-to-text and text-to-speech
- **Pipecat Pipeline**: Implements audio processing pipeline with the following components:
  - Audio input/output handling
  - Voice activity detection (VAD) using Silero
  - Context management with OpenAILLMContext
  - Function calling for order processing
- **Conversation Management**: Handles dialog flow, interruptions, and corrections

### 2. Order Processing Engine

- **Natural Language Understanding**: Processes customer speech into structured order data
- **Order Management**: Tracks current order state, modifications, and confirmations
- **Function Calling**: Uses structured function calls for order operations:
  - add_item: Add new items to the order
  - update_items: Modify existing items (size, combos, etc.)
  - finalize: Complete the order
  - clear: Cancel the current order
- **Smart Detection System**: Automatically detects and corrects LLM function calling errors
  - Combo conversion detection (making items into combos)
  - Protein modification detection (adding proteins to existing items)
  - Size change detection (upgrading/downgrading sizes)
  - Customization update detection (adding/removing customizations)
  - Burrito variant matching (chicken_burrito ↔ burrito)
  - Automatic conversion from add_item to update_items when appropriate
  - Real-time error correction with transparent customer experience
- **Contextual Awareness**: Incorporates time of day and weather information

### 3. Menu Management System

- **Menu Representation**: Hierarchical structure of categories, items, and customizations
- **Pricing Logic**: Handles base prices, customization costs, and combo discounts
- **Dynamic Updates**: Allows menu changes without code modifications
- **Menu Components**:
  - Menu items with base prices and descriptions
  - Size options with price modifiers
  - Combo deals with included items and discounts
  - Customization options with price adjustments
  - Protein and drink options

### 4. Real-time Order Display

- **React Frontend**: Modern, responsive interface for customers at the drive-through
- **Order Visualization**: Clear display of order items, customizations, and pricing in real-time
- **Order Confirmation**: Visual verification of order for customer confirmation
- **Payment Interface**: Display payment screen after order confirmation
- **Order Reset**: Clear display for next customer after payment processing
- **WebSocket Client**: Connects to WebSocket server for real-time updates

### 5. WebSocket Communication Layer

- **Real-time Updates**: Broadcasts order updates to connected clients
- **Connection Management**: Handles client connections, disconnections, and reconnections
- **Message Types**:
  - order_update: Updates to current order items
  - order_finalized: Order confirmation and payment processing
  - order_cleared: Order reset for next customer
- **Message Formatting**: Standardized message format for order updates

### 6. Order Session Management

- **Session Lifecycle**: Manages order creation, modification, and finalization
- **Duplicate Detection**: Prevents accidental duplicate orders within a time threshold
- **Invoice Generation**: Creates unique invoice IDs for each order
- **State Management**: Tracks current order state and items

### 7. Smart Detection System

- **LLM Error Detection**: Automatically identifies when LLM incorrectly uses add_item instead of update_items
- **Pattern Recognition**: Detects combo conversions, protein modifications, size changes, and customization updates
- **Burrito Variant Matching**: Recognizes chicken_burrito and burrito as the same item type for modifications
- **Automatic Correction**: Converts add_item requests to update_items when modification patterns are detected
- **Customer Protection**: Prevents overcharging by eliminating duplicate line items from LLM mistakes
- **Transparent Operation**: Corrections happen seamlessly without customer awareness
- **Comprehensive Logging**: All smart conversions are logged for monitoring and analysis
- **Real-time Updates**: WebSocket integration ensures frontend receives corrected order data immediately

## Technology Stack

### Backend
- **Language**: Python 3.9+
- **Web Framework**: FastAPI
- **WebRTC**: Prebuilt WebRTC UI components
- **Speech Processing**: AWS Nova Sonic
- **Audio Pipeline**: Pipecat
- **WebSockets**: websockets library
- **Async Processing**: asyncio
- **Environment Management**: dotenv

### Frontend
- **Framework**: React
- **State Management**: React Context API or useState hooks
- **UI Components**: Custom CSS
- **WebSocket Client**: native WebSocket API

## Data Models

### Menu Model
```python
class MenuItem:
    id: str
    name: str
    description: str
    base_price: float
    category: str
    available_customizations: List[str]
    available_sizes: Dict[str, float]  # size_name: price_adjustment
    image_url: Optional[str]

class Customization:
    id: str
    name: str
    price_adjustment: float

class ComboMeal:
    id: str
    name: str
    description: str
    items: List[str]  # MenuItem ids
    discount: float
```

### Order Model
```python
class OrderItem:
    item_id: str
    quantity: int
    size: Optional[str]
    combo: bool
    combo_type: Optional[str]
    customizations: List[str]
    protein: Optional[str]
    drink_choice: Optional[str]
    description: str
    price: float

class Order:
    invoice_id: str
    items: List[OrderItem]
    total_price: float
    status: str  # "in_progress", "confirmed", "completed"
    timestamp: datetime
```

### OrderSession Model
```python
class OrderSession:
    current_invoice_id: Optional[str]
    current_order_items: List[OrderItem]
    is_order_active: bool
    last_item_added: Optional[OrderItem]
    last_item_timestamp: float
    duplicate_threshold: float  # seconds
```

### WebSocket Message Models
```python
class OrderUpdateMessage:
    type: str  # "order_update"
    invoice_id: str
    items: List[OrderItem]
    status: str
    timestamp: str

class OrderFinalizedMessage:
    type: str  # "order_finalized"
    order: Order
    status: str
    timestamp: str

class OrderClearedMessage:
    type: str  # "order_cleared"
    invoice_id: str
    timestamp: str
```

## API Endpoints

### HTTP Endpoints
- `GET /client/`: WebRTC client interface
- `POST /api/offer`: WebRTC connection negotiation
- `GET /api/menu`: Retrieve full menu
- `GET /api/orders/{order_id}`: Retrieve order details

### WebSocket Endpoints
- `WS /`: WebSocket endpoint for order updates

## Security Considerations

- WebRTC communication secured with DTLS
- API endpoints protected with rate limiting
- No storage of customer personal information
- Input validation on all API endpoints
- CORS configuration to restrict access to frontend
- **Smart Detection System** provides additional customer protection by preventing overcharging
- Comprehensive logging and monitoring of all order modifications
- Automatic error correction reduces potential for billing disputes

## Deployment Architecture

### Development Environment
- Local development with Docker containers
- Local AWS credential configuration

### Production Environment
- AWS ECS for containerized deployment
- AWS Lambda for serverless components
- Amazon S3 for static frontend hosting
- Amazon CloudFront for content delivery
- AWS Elastic Load Balancer for traffic distribution
