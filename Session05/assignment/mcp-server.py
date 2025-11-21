# basic import 
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
from PIL import Image as PILImage
import math
import sys
import time
import logging
import json
from rich.console import Console
from rich.panel import Panel

# Configure logger to include timestamp and log level. Use DEBUG to log everything.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# instantiate an MCP server client
mcp = FastMCP("Calculator")

# Price data structure
prices = {
    "TATA": {
        "HARRIER": {
            "DIESEL": {
                "AUTOMATIC": {
                    "PUREXAT": 2303000,
                    "ADVENTUREXAT": 1957000,
                    "FEARLESSXAT": 2845000
                },
                "MANUAL": {
                    "SMART": 1747000,
                    "PUREX": 2116000,
                    "ADVENTUREX": 2234000,
                    "FEARLESSX": 2641000
                }
            },
            "ELECTRIC": {
                "AUTOMATIC": {
                    "ADVENTURE65": 2326000,
                    "FEARLESSPLUS65": 2592000,
                    "EMPOWERED75": 3256000,
                    "EMPOWEREDQWD75": 3432000
                }
            }
        }
    }
}

@mcp.tool()
def getPrice(brand : str, model : str, fuel_type : str, transmission : str, variant : str) -> int:
    """Get ex-showroom price for car with given brand, model, fuel type, transmission, and variant"""
    return prices[brand.upper][model.upper][fuel_type.upper][transmission.upper][variant.upper]

@mcp.tool()
def variants(brand: str, model: str, fuel_type: str, transmission: str) -> list:
    """Get variants for a specific brand, model, fuel type, and transmission"""
    logger.info(f"Fetching variants for {brand}, {model}, {fuel_type}, {transmission}")
    brand = brand.upper().strip()
    model = model.upper().strip()
    fuel_type = fuel_type.upper().strip()
    transmission = transmission.upper().strip()

    try:
        if prices[brand][model][fuel_type][transmission]:
            logger.info(f"Variants found: {list(prices[brand][model][fuel_type][transmission].keys())}")
            return list(prices[brand][model][fuel_type][transmission].keys())
    except KeyError:
        pass
    return []

@mcp.tool()
def ex_showroom_price(brand: str, model: str, fuel_type: str, transmission: str, variant: str) -> int:
    """Get ex-showroom price for given brand, model, fuel type, transmission, and variant"""
    brand = brand.upper().strip()
    model = model.upper().strip()
    fuel_type = fuel_type.upper().strip()
    transmission = transmission.upper().strip()
    variant = variant.upper().strip()
    logger.info(f"Fetching ex-showroom price for {brand}, {model}, {fuel_type}, {transmission}, {variant}")

    try:
        if prices[brand][model][fuel_type][transmission][variant]:
            logger.info(f"Ex-showroom price found: {prices[brand][model][fuel_type][transmission][variant]}")
            return prices[brand][model][fuel_type][transmission][variant]
    except KeyError:
        pass
    return -1

@mcp.tool()
def road_tax_multiplier(state: str, ex_showroom_price: int, fuel_type: str) -> float:
    """Calculate road tax multiplier based on state, price, and fuel type"""
    logger.info(f"Calculating road tax multiplier for {state}, {ex_showroom_price}, {fuel_type}")
    if int(ex_showroom_price) > 2500000:
        above25 = True
    else:
        above25 = False

    if fuel_type == "ELECTRIC" and above25:
        if state in ["DELHI", "TAMILNADU", "HYDERABAD", "MAHARASHTRA",
                     "ODISHA", "PUNJAB", "WESTBENGAL", "MEGHALAYA", "BIHAR", "TELANGANA"]:
            return 0
        if state in ["GUJARAT", "KERALA"]:
            return 0.05
    if fuel_type == "DIESEL":
        return 0.125

    return 0.1

@mcp.tool()
def on_road_price(ex_showroom_price: int, road_tax_multiplier: float) -> int:
    """Calculate on-road price"""
    ex_showroom_price = int(ex_showroom_price)
    road_tax_multiplier = float(road_tax_multiplier)
    road_tax = int(ex_showroom_price * road_tax_multiplier)
    state_development_fee = 4000
    registration_charges = 600
    fastag = 600
    hypothecation_endorsement = 1500
    other_charges = 400
    insurance = int(ex_showroom_price * 0.05)

    logger.info(
        f"Calculating on-road price with ex_showroom_price: {ex_showroom_price}, road_tax: {road_tax}, state_development_fee: {state_development_fee}, registration_charges: {registration_charges}, fastag: {fastag}, hypothecation_endorsement: {hypothecation_endorsement}, other_charges: {other_charges}, insurance: {insurance}")
    
    return ex_showroom_price + road_tax + state_development_fee + registration_charges + fastag + hypothecation_endorsement + other_charges + insurance

# DEFINE RESOURCES

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    print("CALLED: get_greeting(name: str) -> str:")
    return f"Hello, {name}!"


# DEFINE AVAILABLE PROMPTS
@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"
    # print("CALLED: review_code(code: str) -> str:")


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]

if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING THE SERVER AT AMAZING LOCATION")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
