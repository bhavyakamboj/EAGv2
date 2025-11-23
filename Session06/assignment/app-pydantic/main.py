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
from models import PreferencesOutput
import perception
import decision
import action
from perception import find_facts
from memory import recall

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
iteration = 0
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

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response, preferences
    last_response = None
    iteration = 0
    iteration_response = []
    preferences = None

async def process_query(query: str):
    reset_state()  # Reset at the start of main

    facts = await find_facts(query)
    # import pdb; pdb.set_trace()
    preferences = await recall(query)

    try:
        # Create a single MCP server connection
        console.print("[yellow]Establishing connection to MCP server...[/yellow]")
        server_params = StdioServerParameters(
            command="python",
            args=["mcp-server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            console.print("[yellow]Connection established, creating session...[/yellow]")
            async with ClientSession(read, write) as session:
                console.print("[yellow]Session created, initializing...[/yellow]")
                await session.initialize()
                
                
                # Get available tools
                console.print("[yellow]Requesting tool list...[/yellow]")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                console.print(f"[green]Successfully retrieved {len(tools)} tools[/green]")

                # Create system prompt with available tools
                print("Creating system prompt...")
                print(f"Number of tools: {len(tools)}")
                
                try:
                    # First, let's inspect what a tool object looks like
                    # if tools:
                    #     print(f"First tool properties: {dir(tools[0])}")
                    #     print(f"First tool example: {tools[0]}")
                    
                    tools_description = []
                    for i, tool in enumerate(tools):
                        try:
                            # Get tool properties
                            params = tool.inputSchema
                            desc = getattr(tool, 'description', 'No description available')
                            name = getattr(tool, 'name', f'tool_{i}')
                            
                            # Format the input schema in a more readable way
                            if 'properties' in params:
                                param_details = []
                                for param_name, param_info in params['properties'].items():
                                    param_type = param_info.get('type', 'unknown')
                                    param_details.append(f"{param_name}: {param_type}")
                                params_str = ', '.join(param_details)
                            else:
                                params_str = 'no parameters'

                            tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                            tools_description.append(tool_desc)
                            print(f"Added description for tool: {tool_desc}")

                        except Exception as e:
                            print(f"[red]Error processing tool {i}: {e}[/red]")
                            tools_description.append(f"{i+1}. Error processing tool")
                    
                    tools_description = "\n".join(tools_description)
                    console.print("[green]Successfully created tools description[/green]")

                except Exception as e:
                    console.print(f"[red]Error creating tools description: {e}[/red]")

                    tools_description = "Error loading tools"
                
                console.print("[green]Created system prompt...[/green]")
                
                # Only evaluate prompt for Decision layer
                system_prompt = await decision.get_system_prompt(tools_description)
                
                # Evaluate the decision system prompt
                await evaluate_decision_prompt(system_prompt)
                
                # Use global iteration variables
                global iteration, last_response
                context = ""
                
                while iteration < max_iterations:
                    time.sleep(1)  # brief pause to avoid overwhelming the LLM
                    print(f"\n--- Iteration {iteration + 1} ---")
                    if last_response is None:
                        current_query = query
                    else:
                        current_query = current_query + "\n\n" + " ".join(iteration_response)
                        # current_query = current_query + "  What should I do next?"

                    
                    print("Invoking decision layer...")
                    response_text = await decision.perform_decision(facts, preferences, current_query, tools_description, last_response)
                    

                    if response_text.startswith("FUNCTION_CALL:"):
                        try:
                            
                            # Action layer activated
                            action_result = await action.perform_action(action=response_text)
                            import pdb; pdb.set_trace()
                            if hasattr(action_result, 'content'):
                                print(f"DEBUG: Result has content attribute")
                                if isinstance(action_result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in iteration_result.content
                                    ]
                                else:
                                    iteration_result = str(iteration_result.content)
                            else:
                                print(f"DEBUG: Result has no content attribute")
                                iteration_result = str(action_result.result)

                            print(f"DEBUG: Final iteration result: {iteration_result}")

                            result_str = f"[{', '.join(iteration_result)}]" if isinstance(iteration_result, list) else str(iteration_result)

                            iteration_response.append(
                                f"In the {iteration + 1} iteration you called {action_result.func_name} with {action_result.arguments} parameters, "
                                f"and the function returned {result_str}."
                            )
                            last_response = iteration_result

                        except Exception as e:
                            print(f"DEBUG: Error details: {str(e)}")
                            print(f"DEBUG: Error type: {type(e)}")
                            import traceback
                            traceback.print_exc()
                            iteration_response.append(f"Error in iteration {iteration + 1}: {str(e)}")
                            break


                    elif response_text.startswith("FINAL_ANSWER:"):
                        print("\n=== Agent Execution Complete ===")

                        break

                    iteration += 1

        return {
            "status": "completed",
            "iterations": iteration,
            "final_response": last_response
        }

    except Exception as e:
        console.print(f"[red]Error in main execution: {e}[/red]")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e),
            "iterations": iteration
        }
    finally:
        reset_state()  # Reset at the end of main


async def evaluate_decision_prompt(system_prompt):
    """Evaluate the decision system prompt using the decision layer"""
    with open("prompt_of_prompts.md", "r", encoding='utf-8') as file:
        evaluation_prompt = file.read()

    # query = """Find the on road price of a car with brand as "Tata", model as "Harrier", fuel type as "Diesel", transmission as "Automatic" and state as "Delhi"."""
    print("Starting iteration loop...")
    
    # Evaluate the system prompt before proceeding
    print("\n--- Evaluating System Prompt ---")
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

async def process_preferences(preferences: str):
    import memory
    from memory import MemoryItem

    item = MemoryItem(fact=preferences, importance = 0.9, source="api")
    await memory.store(item)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/v1/chat', methods=['POST'])
def chat():
    """API endpoint to process queries"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            console.print("[red]Error: Missing 'query' field in request body[/red]")

            return jsonify({"error": "Missing 'query' field in request body"}), 400
        
        query = data['query']
        app.logger.info(f"Received query: {query}")
        
        # Process the query by running the async function
        result = asyncio.run(process_query(query))
        
        return jsonify(result), 200
    
    except Exception as e:
        console.print(f"[red]Error processing request: {str(e)}[/red]")

        return jsonify({"error": str(e)}), 500
    
@app.route('/v1/preferences', methods=['POST'])
def set_preferences():
    """API endpoint to process preferences"""
    try:
        data = request.get_json()
        
        if not data or 'preferences' not in data:
            console.print("[red]Error: Missing 'preferences' field in request body[/red]")

            return jsonify({"error": "Missing 'preferences' field in request body"}), 400
        
        preferences = data['preferences']
        app.logger.info(f"Received preferences: {preferences}")
        
        # Process the query by running the async function
        result = asyncio.run(process_preferences(preferences))
        
        return jsonify(result), 200
    
    except Exception as e:
        console.print(f"[red]Error processing request: {str(e)}[/red]")

        return jsonify({"error": str(e)}), 500
    
@app.route('/v1/preferences', methods=['GET'])
def get_preferences():
    """API endpoint to get preferences"""
    import memory
    try:        
        # Process the query by running the async function
        memory_items = asyncio.run(memory.list())

        memory_json = [i.json() for i in memory_items]    
        return {"preferences": memory_json}, 200
    
    except Exception as e:
        console.print(f"[red]Error processing request: {str(e)}[/red]")

        return jsonify({"error": str(e)}), 500
    
@app.route('/v1/preferences', methods=['DELETE'])
def delete_preferences():
    """API endpoint to delete preferences"""
    import memory
    try:        
        # Process the query by running the async function
        asyncio.clear_memories()

        return None, 200
    
    except Exception as e:
        console.print(f"[red]Error processing request: {str(e)}[/red]")

        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
