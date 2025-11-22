import os
from dotenv import load_dotenv
from google import genai
import asyncio
from concurrent.futures import TimeoutError
from rich.console import Console
from rich.panel import Panel

console = Console()

# Load environment variables and setup Gemini
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)  

async def generate_content_with_timeout(client, prompt, timeout=10):
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
    
async def process_perception(prompt):
    """Process perception input and get LLM response"""
    response = await generate_content_with_timeout(client, prompt)
    if response and response.text:
        return response.text.strip()
    return None



async def main():
    print("Hello")

if __name__ == "__main__":
    asyncio.run(main())