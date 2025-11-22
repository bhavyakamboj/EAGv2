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
from models import PriceInput, PriceOutput, VariantsInput, VariantsOutput, ExShowroomPriceInput, ExShowroomPriceOutput, RoadTaxMultiplierInput, RoadTaxMultiplierOutput, OnRoadPriceInput, OnRoadPriceOutput, PreferencesOutput

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
def getPrice(input: PriceInput) -> PriceOutput:
    """Get ex-showroom price for car with given brand, model, fuel type, transmission, and variant"""
    return prices[str(input.brand).upper][str(input.model).upper][str(input.fuel_type).upper][str(input.transmission).upper][str(input.variant).upper]

@mcp.tool()
def variants(input: VariantsInput) -> VariantsOutput:
    """Get variants for a specific brand, model, fuel type, and transmission"""
    logger.info(f"Fetching variants for {input}")

    return {'variants': list(prices[input.brand.upper().strip()][input.model.upper().strip()][input.fuel_type.upper().strip()][input.transmission.upper().strip()].keys())}

@mcp.tool()
def ex_showroom_price(input: ExShowroomPriceInput) -> ExShowroomPriceOutput:
    """Get ex-showroom price for given brand, model, fuel type, transmission, and variant"""

    logger.info(f"Fetching ex-showroom price for {input}")

    return {'ex_showroom_price': prices[input.brand.upper().strip()][input.model.upper().strip()][input.fuel_type.upper().strip()][input.transmission.upper().strip()][input.variant.upper().strip()]}

@mcp.tool()
def road_tax_multiplier(input: RoadTaxMultiplierInput) -> RoadTaxMultiplierOutput:
    """Calculate road tax multiplier based on state, price, and fuel type"""
    logger.info(f"Calculating road tax multiplier for {input.state}, {input.ex_showroom_price}, {input.fuel_type}")
    if int(input.ex_showroom_price) > 2500000:
        above25 = True
    else:
        above25 = False

    if input.fuel_type == "ELECTRIC" and above25:
        if input.state in ["DELHI", "TAMILNADU", "HYDERABAD", "MAHARASHTRA",
                     "ODISHA", "PUNJAB", "WESTBENGAL", "MEGHALAYA", "BIHAR", "TELANGANA"]:
            return {'multiplier': 0}
        if input.state in ["GUJARAT", "KERALA"]:
            return {'multiplier': 0.05}
    if input.fuel_type == "DIESEL":
        return {'multiplier': 0.125}

    return {'multiplier': 0.1}

@mcp.tool()
def on_road_price(input: OnRoadPriceInput) -> OnRoadPriceOutput:
    """Calculate on-road price"""
    road_tax = input.ex_showroom_price * input.road_tax_multiplier
    state_development_fee = 4000
    registration_charges = 600
    fastag = 600
    hypothecation_endorsement = 1500
    other_charges = 400
    insurance = input.ex_showroom_price * 0.05  # Assuming insurance is 5% of ex-showroom price

    logger.info(
        f"Calculating on-road price with ex_showroom_price: {input.ex_showroom_price}, road_tax: {road_tax}, state_development_fee: {state_development_fee}, registration_charges: {registration_charges}, fastag: {fastag}, hypothecation_endorsement: {hypothecation_endorsement}, other_charges: {other_charges}, insurance: {insurance}")
    
    return {'on_road_price': float(input.ex_showroom_price + road_tax + state_development_fee + registration_charges + fastag + hypothecation_endorsement + other_charges + insurance)}

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
