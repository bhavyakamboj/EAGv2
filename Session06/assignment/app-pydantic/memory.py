import os
from dotenv import load_dotenv
from google import genai
import asyncio
from concurrent.futures import TimeoutError
from rich.console import Console
from rich.panel import Panel
from models import PreferencesOutput
from pydantic import BaseModel
from typing import Optional, List
from pydantic_core import from_json

console = Console()

# Load environment variables and setup Gemini
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)  

class MemoryItem(BaseModel):
    fact: str
    importance: float
    source: Optional[str] = None

memory = []

def __init__(self):
    self.memory = []

async def store(input: MemoryItem):
    """Stores a memory item to the memory list"""
    memory.append(input)
    console.print(Panel(f"Added memory: {input.fact} (Importance: {input.importance})", border_style="green"))

async def recall(query):
    prompt = f"Given the memory: {memory}, answer : {query}"
    return await call_llm(prompt)

async def list():
    return memory

async def clear_memories():
    """Clear all memory items"""
    memory.clear()
    console.print(Panel("Cleared all memories", border_style="red"))


async def generate_with_timeout(client, prompt, timeout=10)->PreferencesOutput:
    """Generate content with a timeout"""
    try:
        console.print(Panel("Perception Layer", border_style="magenta"))
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
        console.print("[red]Error: Generation timed out[/red]")
        return None         
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return None
    
async def call_llm(prompt):
    """Process perception input and get LLM response"""
    response = await generate_with_timeout(client, prompt)
    if response and response.text:
        return response.text.strip()
    return None
