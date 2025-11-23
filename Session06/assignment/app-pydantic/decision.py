import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
from concurrent.futures import TimeoutError
from functools import partial
import json, time
from rich.console import Console
from rich.panel import Panel
from models import FactsOutput, PreferencesOutput
import action

console = Console()



# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

max_iterations = 10
last_response = None
iteration_response = []
preferences:PreferencesOutput = None

async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout"""
    try:
        console.print(Panel("Car on-road price calculator.", border_style="magenta"))
        # Convert the synchronous generate_content call to run in a thread
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
            ),
            timeout=timeout
        )
        print("LLM generation completed")
        return response
    except TimeoutError:
        console.print("[red]LLM generation timed out![/red]")
        raise
    except Exception as e:
        print(f"[red]Error in LLM generation: {e}[/red]")
        raise


async def perform_decision(facts: FactsOutput, preference: PreferencesOutput, query: str, tools_description: str, last_response: str):
    """Perform decision making using the decision layer"""

    system_prompt = await get_system_prompt(tools_description)

    current_query = query + "  What should I do next?"

    # Get model's response with timeout

    decision_prompt = f"Facts: {facts}\n\nPreferences: {preferences}\n\nTools :{tools_description}\n\nSystem prompt: {system_prompt}\n\nQuery: {current_query}"

    # console.print(f"[blue]Prompt sent to model:[/blue]\n{prompt}\n")
    try:
        response = await generate_with_timeout(client, decision_prompt)
        response_text = response.text.strip()
        print(f"LLM Response: {response_text}")
        
        # Find the FUNCTION_CALL line in the response
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith("FUNCTION_CALL:"):
                response_text = line
                break
        
        return response_text
    except Exception as e:
        print(f"Failed to get LLM response: {e}")


async def get_system_prompt(tools_description: str) -> str:
    return f"""
    You are a decision agent. You have access to various tools.

    Available tools:
    {tools_description}

    You must respond with EXACTLY ONE line in one of these formats (no additional text):

    1. For function calls (using key=value format):
    FUNCTION_CALL: function_name|param1=value1|param2=value2|...

    - You can also use nested keys for structured inputs (e.g., input.string, input.int_list).
    - For list-type inputs, use square brackets: input.int_list=[73,78,68,73,65]

    2. For final answers:
    FINAL_ANSWER: [number]

    Important:
    - Use exactly one FUNCTION_CALL or FINAL_ANSWER per step.
    - Do not repeat function calls with the same parameters.
    - Do not include explanatory text or formatting.
    - When a function returns multiple values, you must process all of them.

    ✅ Examples:
    - FUNCTION_CALL: variants|input.brand=TATA|input.model=HARRIER|input.fuel_type=DIESEL|input.transmission=AUTOMATIC
    - FUNCTION_CALL: ex_showroom_price|input.brand=TATA|input.model=HARRIER|input.fuel_type=DIESEL|input.transmission=AUTOMATIC|input.variant=PUREXAT
    - FUNCTION_CALL: road_tax_multiplier|input.state=DELHI|input.ex_showroom_price=2303000|input.fuel_type=DIESEL
    - FUNCTION_CALL: on_road_price|input.ex_showroom_price=2303000|input.road_tax_multiplier=1.12
    - FINAL_ANSWER: 2579360.0

    DO NOT include any explanations or extra text.
    Your entire response must be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER: 
    """