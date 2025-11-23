import os
from dotenv import load_dotenv
from google import genai
import asyncio
from concurrent.futures import TimeoutError
from rich.console import Console
from rich.panel import Panel
from models import FactsOutput
from pydantic_core import from_json
import memory

console = Console()

# Load environment variables and setup Gemini
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)  

async def generate_with_timeout(client, prompt, timeout=10)->FactsOutput:
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
    response = await generate_with_timeout(client, prompt)
    if response and response.text:
        return response.text.strip()
    return None


async def find_facts(query: str) -> FactsOutput:
    """Get facts from query using perception layer"""
    system_prompt = f"""
        You are a perception agent that extracts facts from the user query using explicit, verifiable reasoning steps. You complete the request in the sequence - reason, act, and verify.

        ### OUTPUT FORMAT
        You must respond with a SINGLE valid JSON object. Do not include markdown formatting (like ```json). The Json object has to be directly parsable by the FactsOutput Pydantic model. So do not add any character before and after the JSON object. IT IS IMPORTANT.
        The JSON must strictly follow this schema:

        {FactsOutput.schema_json(indent=4)}

        ### Example
        For user query: "Find the on road price of a car with brand as "Tata", model as "Harrier", fuel type as "Diesel", transmission as "Automatic" and state in "Delhi" or "Karnataka" or "TamilNadu". My budget is from 15 lakhs to 25 lakhs"
        Correct Output:
        {{
        "state": [
            "Delhi",
            "Karnataka",
            "TamilNadu"
        ],
        "fuel_type": "Diesel",
        "transmission": "Automatic",
        "minPrice": 1500000,
        "maxPrice": 2000000
        }}

        InCorrect Output:
        ```json{{}}```

        ### REASONING & BEHAVIOR RULES
        1. **Trace Your Thoughts:** Fill the `thought_trace` field before deciding on an action. Explain *why* you are taking the next step.
        2. **Categorize:** Explicitly label your logic in `reasoning.type`.
        3. **Verify Inputs:** Before calling a function, ensure you have all required arguments in the `self_check` field.
        4. **Safety Fallback:** If `self_check.status` is "FAIL" or if you lack information, set `action.type` to "ERROR" and ask the user for missing information.
        5. **Tool Separation:** Never perform any math or logic operations yourself. Your only goal is to extract preferences based on user query.
        6. **Iterative Flow:** Use the output provided by the user (from previous tool calls) to inform your next JSON response.
        7. **When to Stop:** Populate the preference object with available values only. Leave unknown fields as null or default type. Do not guess or fabricate values."""
        
        # import pdb; pdb.set_trace()
    print("{system_prompt}")

    with open("prompt_of_prompts.md", "r", encoding='utf-8') as file:
        evaluation_prompt = file.read()

    # query = """Find the on road price of a car with brand as "Tata", model as "Harrier", fuel type as "Diesel", transmission as "Automatic" and state in "Delhi" or "Karnataka" or "TamilNadu". Budget is from 15 lakhs to 25 lakhs"""
    print("Starting iteration loop...")
    
    # Evaluate the system prompt before proceeding
    print("\n--- Evaluating Perception Layer System Prompt ---")
    try:
        system_prompt_evaluation = await generate_with_timeout(
            client, 
            f"{evaluation_prompt}\n\nSystem Prompt to evaluate:\n{system_prompt}"
        )
        evaluation_result = system_prompt_evaluation.text.strip()
        console.print(f"System Prompt Evaluation Result:\n[green]{evaluation_result}[/green]")
        print("Evaluation completed. Proceeding with main loop...\n")
    except Exception as e:
        console.print(f"[red]Error evaluating system prompt: {e}[/red]")
        evaluation_result = None
    
    prompt = f"{system_prompt}\n\nPerception Agent Query: {query}\n\nRespond with the required JSON object."
    response = await generate_with_timeout(client, prompt)
    correctedResponse =  response.text.replace("```json", "").replace("```", "").strip()


    try:
        console.print(correctedResponse)
        FactsOutput.model_validate_json(correctedResponse)
        console.print("[green]Successfully validated the response against FactsOutput schema.[/green]")
        result = FactsOutput.model_validate(from_json(correctedResponse))

        return result
    except Exception as e:
        console.print(f"[red]Response validation failed: {e}[/red]")
        raise e