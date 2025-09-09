"""
API endpoints for the GrillTalk system.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
from menu import MENU_ITEMS, SIZES, COMBOS, CUSTOMIZATIONS, PROTEIN_OPTIONS, DRINK_OPTIONS

# Create API router
router = APIRouter()

# Define response models
class MenuItem(BaseModel):
    id: str
    name: str
    base_price: float
    description: str

class SizeOption(BaseModel):
    id: str
    name: str
    price_modifier: float
    description: str

class ComboOption(BaseModel):
    id: str
    name: str
    includes: List[str]
    discount: float
    description: str
    size: Optional[str] = None

class CustomizationOption(BaseModel):
    id: str
    name: str
    price: float

class ProteinOption(BaseModel):
    id: str
    name: str
    price: float

class DrinkOption(BaseModel):
    id: str
    name: str

class MenuResponse(BaseModel):
    menu_items: Dict[str, MenuItem]
    sizes: Dict[str, SizeOption]
    combos: Dict[str, ComboOption]
    customizations: Dict[str, CustomizationOption]
    protein_options: Dict[str, ProteinOption]
    drink_options: Dict[str, DrinkOption]

# API endpoints
@router.get("/api/menu", response_model=MenuResponse)
async def get_menu():
    """Get the full menu with all options."""
    try:
        # Convert menu items to response model
        menu_items_dict = {
            item_id: MenuItem(
                id=item_id,
                name=item["name"],
                base_price=item["base_price"],
                description=item["description"]
            ) for item_id, item in MENU_ITEMS.items()
        }
        
        # Convert sizes to response model
        sizes_dict = {
            size_id: SizeOption(
                id=size_id,
                name=size["name"],
                price_modifier=size["price_modifier"],
                description=size["description"]
            ) for size_id, size in SIZES.items()
        }
        
        # Convert combos to response model
        combos_dict = {
            combo_id: ComboOption(
                id=combo_id,
                name=combo["name"],
                includes=combo["includes"],
                discount=combo["discount"],
                description=combo["description"],
                size=combo.get("size")
            ) for combo_id, combo in COMBOS.items()
        }
        
        # Convert customizations to response model
        customizations_dict = {
            custom_id: CustomizationOption(
                id=custom_id,
                name=CUSTOMIZATIONS[custom_id]["name"],
                price=CUSTOMIZATIONS[custom_id]["price"]
            ) for custom_id in CUSTOMIZATIONS
        }
        
        # Convert protein options to response model
        protein_dict = {
            protein_id: ProteinOption(
                id=protein_id,
                name=PROTEIN_OPTIONS[protein_id]["name"],
                price=PROTEIN_OPTIONS[protein_id]["price"]
            ) for protein_id in PROTEIN_OPTIONS
        }
        
        # Convert drink options to response model
        drink_dict = {
            drink_id: DrinkOption(
                id=drink_id,
                name=DRINK_OPTIONS[drink_id]
            ) for drink_id in DRINK_OPTIONS
        }
        
        return MenuResponse(
            menu_items=menu_items_dict,
            sizes=sizes_dict,
            combos=combos_dict,
            customizations=customizations_dict,
            protein_options=protein_dict,
            drink_options=drink_dict
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve menu: {str(e)}")

@router.get("/api/menu/items", response_model=Dict[str, MenuItem])
async def get_menu_items():
    """Get all menu items."""
    try:
        return {
            item_id: MenuItem(
                id=item_id,
                name=item["name"],
                base_price=item["base_price"],
                description=item["description"]
            ) for item_id, item in MENU_ITEMS.items()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve menu items: {str(e)}")

@router.get("/api/menu/items/{item_id}", response_model=MenuItem)
async def get_menu_item(item_id: str):
    """Get a specific menu item by ID."""
    if item_id not in MENU_ITEMS:
        raise HTTPException(status_code=404, detail=f"Menu item '{item_id}' not found")
    
    try:
        item = MENU_ITEMS[item_id]
        return MenuItem(
            id=item_id,
            name=item["name"],
            base_price=item["base_price"],
            description=item["description"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve menu item: {str(e)}")

@router.get("/api/menu/sizes", response_model=Dict[str, SizeOption])
async def get_sizes():
    """Get all available sizes."""
    try:
        return {
            size_id: SizeOption(
                id=size_id,
                name=size["name"],
                price_modifier=size["price_modifier"],
                description=size["description"]
            ) for size_id, size in SIZES.items()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sizes: {str(e)}")

@router.get("/api/menu/combos", response_model=Dict[str, ComboOption])
async def get_combos():
    """Get all available combo options."""
    try:
        return {
            combo_id: ComboOption(
                id=combo_id,
                name=combo["name"],
                includes=combo["includes"],
                discount=combo["discount"],
                description=combo["description"],
                size=combo.get("size")
            ) for combo_id, combo in COMBOS.items()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve combos: {str(e)}")

@router.get("/api/menu/customizations", response_model=Dict[str, CustomizationOption])
async def get_customizations():
    """Get all available customization options."""
    try:
        return {
            custom_id: CustomizationOption(
                id=custom_id,
                name=CUSTOMIZATIONS[custom_id]["name"],
                price=CUSTOMIZATIONS[custom_id]["price"]
            ) for custom_id in CUSTOMIZATIONS
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve customizations: {str(e)}")

@router.get("/api/menu/proteins", response_model=Dict[str, ProteinOption])
async def get_proteins():
    """Get all available protein options."""
    try:
        return {
            protein_id: ProteinOption(
                id=protein_id,
                name=PROTEIN_OPTIONS[protein_id]["name"],
                price=PROTEIN_OPTIONS[protein_id]["price"]
            ) for protein_id in PROTEIN_OPTIONS
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve protein options: {str(e)}")

@router.get("/api/current-order")
async def get_current_order():
    """Get the current active order."""
    try:
        from food_ordering import current_order_session
        
        if not current_order_session.is_order_active:
            return {"status": "no_active_order", "message": "No active order"}
        
        return {
            "status": "active_order",
            "invoice_id": current_order_session.current_invoice_id,
            "items": current_order_session.current_order_items,
            "total_items": len(current_order_session.current_order_items),
            "total_price": sum(item["price"] for item in current_order_session.current_order_items),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve current order: {str(e)}")

@router.get("/api/websocket-orders")
async def get_websocket_orders():
    """Get all orders stored in WebSocket server."""
    try:
        from websocket_server import orders_store
        return {
            "status": "success",
            "orders": dict(orders_store),
            "count": len(orders_store)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve WebSocket orders: {str(e)}")

class DriveThruMessage(BaseModel):
    message: str

@router.post("/api/drive-thru-message")
async def send_drive_thru_message(message_data: DriveThruMessage):
    """Send drive-thru completion message via LLM."""
    try:
        # Send the drive-thru message via LLM
        drive_thru_text = message_data.message or "Thank you for your order! Please drive to the next window to collect your food."
        
        # Log the message for now (agent integration can be added later)
        print(f"Drive-thru message: {drive_thru_text}")
        
        return {
            "status": "success", 
            "message": "Drive-thru message sent",
            "text": drive_thru_text,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error in drive-thru message endpoint: {e}")
        return {
            "status": "error", 
            "message": f"Failed to send drive-thru message: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
