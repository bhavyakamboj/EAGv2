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

console = Console()

def parse_function_call_params(param_parts: list[str]) -> dict:
    """
    Parses key=value parts from the FUNCTION_CALL format.
    Supports nested keys like input.string=foo and list values like input.int_list=[1,2,3]
    Returns a nested dictionary.
    """
    result = {}

    for part in param_parts:
        if "=" not in part:
            raise ValueError(f"Invalid parameter format (expected key=value): {part}")

        key, value = part.split("=", 1)

        # Try to parse as Python literal (int, float, list, etc.)
        try:
            parsed_value = ast.literal_eval(value)
        except Exception:
            parsed_value = value.strip()

        # Support nested keys like input.string
        keys = key.split(".")
        current = result
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = parsed_value

    return result

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

    from perception import find_preferences

    preferences = await find_preferences(query)


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
                
                system_prompt = f"""
                You are a math agent solving problems in iterations. You have access to various mathematical tools.

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
                
                # import pdb; pdb.set_trace()
                # print("{system_prompt}")

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
                        current_query = current_query + "  What should I do next?"

                    # Get model's response with timeout
                    print("Preparing to generate LLM response...")
                    prompt = f"Preferences: {preferences}\n\n{system_prompt}\n\nQuery: {current_query}"
                    # console.print(f"[blue]Prompt sent to model:[/blue]\n{prompt}\n")
                    try:
                        response = await generate_with_timeout(client, prompt)
                        response_text = response.text.strip()
                        print(f"LLM Response: {response_text}")
                        
                        # Find the FUNCTION_CALL line in the response
                        for line in response_text.split('\n'):
                            line = line.strip()
                            if line.startswith("FUNCTION_CALL:"):
                                response_text = line
                                break
                        
                    except Exception as e:
                        print(f"Failed to get LLM response: {e}")
                        break


                    if response_text.startswith("FUNCTION_CALL:"):
                        _, function_info = response_text.split(":", 1)
                        parts = [p.strip() for p in function_info.split("|")]
                        func_name, param_parts = parts[0], parts[1:]

                        print(f"\nDEBUG: Raw function info: {function_info}")
                        print(f"DEBUG: Split parts: {parts}")
                        print(f"DEBUG: Function name: {func_name}")
                        print(f"DEBUG: Raw parameters: {param_parts}")

                        try:
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                print(f"DEBUG: Available tools: {[t.name for t in tools]}")
                                raise ValueError(f"Unknown tool: {func_name}")

                            print(f"DEBUG: Found tool: {tool.name}")
                            print(f"DEBUG: Tool schema: {tool.inputSchema}")

                            arguments = parse_function_call_params(param_parts)
                            print(f"DEBUG: Final arguments: {arguments}")
                            print(f"DEBUG: Calling tool {func_name}")

                            result = await session.call_tool(func_name, arguments=arguments)
                            print(f"DEBUG: Raw result: {result}")

                            if hasattr(result, 'content'):
                                print(f"DEBUG: Result has content attribute")
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in result.content
                                    ]
                                else:
                                    iteration_result = str(result.content)
                            else:
                                print(f"DEBUG: Result has no content attribute")
                                iteration_result = str(result)

                            print(f"DEBUG: Final iteration result: {iteration_result}")

                            result_str = f"[{', '.join(iteration_result)}]" if isinstance(iteration_result, list) else str(iteration_result)

                            iteration_response.append(
                                f"In the {iteration + 1} iteration you called {func_name} with {arguments} parameters, "
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)